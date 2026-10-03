import hashlib
import hmac
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import UUID

import pytest
from conftest import headers, prepare_open
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from app.allocation import draw
from app.allocation.crypto import manifest_bytes, reveal_seed
from app.core.clock import db_now
from app.core.errors import DomainError
from app.drops import service
from app.persistence import models as m


def close_due(api, actors, factory, drop_id):
    with factory.begin() as db:
        drop = db.get(m.Drop, UUID(drop_id))
        drop.ends_at = db_now(db) - timedelta(milliseconds=1)
    response = api.post(f"/api/v1/admin/drops/{drop_id}/close", json={}, headers=headers(actors[0]))
    assert response.status_code == 200, response.text
    return response


def wait_until_deadline(factory, drop_id):
    with factory() as db:
        deadline = db.get(m.Drop, UUID(drop_id)).ends_at
        while db_now(db) < deadline:
            time.sleep(0.01)


def test_close_waits_for_admission_and_freezes_committed_entry(api, actors, draft_payload, factory):
    drop_id = prepare_open(api, actors, draft_payload, factory)
    with factory.begin() as db:
        drop = db.get(m.Drop, UUID(drop_id))
        drop.ends_at = db_now(db) + timedelta(milliseconds=200)
    admission = factory()
    entry, inserted = service.enter(admission, UUID(drop_id), actors[1])
    assert inserted
    wait_until_deadline(factory, drop_id)

    def close():
        with factory.begin() as db:
            drop = service.lock_drop(db, UUID(drop_id))
            draw.close_drop(db, drop)

    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(close)
        # Confirm the close actually reached a PostgreSQL lock wait.
        with factory() as observer:
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                waiting = observer.scalar(
                    text(
                        "SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND wait_event_type='Lock'"
                    )
                )
                if waiting:
                    break
                time.sleep(0.01)
            assert waiting
        assert not pending.done()
        admission.commit()
        pending.result(timeout=5)
    admission.close()
    with factory() as db:
        run = db.scalar(select(m.DrawRun))
        frozen = list(db.scalars(select(m.FrozenEntry)))
        assert run.total_entries == 1 and run.snapshot_sealed
        assert frozen[0].entry_id == entry.id
    late = api.post(f"/api/v1/drops/{drop_id}/entries", json={}, headers=headers(actors[2]))
    assert late.status_code == 409


def test_admission_wait_reads_fresh_wall_clock(api, actors, draft_payload, factory):
    drop_id = prepare_open(api, actors, draft_payload, factory)
    with factory.begin() as db:
        drop = db.get(m.Drop, UUID(drop_id))
        drop.ends_at = db_now(db) + timedelta(milliseconds=200)
    blocker = factory()
    service.lock_drop(blocker, UUID(drop_id))

    def admit():
        with factory.begin() as db:
            return service.enter(db, UUID(drop_id), actors[1])

    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(admit)
        wait_until_deadline(factory, drop_id)
        blocker.commit()
        with pytest.raises(DomainError) as error:
            pending.result(timeout=5)
        assert error.value.code == "ENTRY_CLOSED"
    blocker.close()
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(m.Entry)) == 0


def test_concurrent_draws_canonical_scores_and_snapshot_immutability(
    api, actors, draft_payload, factory
):
    drop_id = prepare_open(api, actors, draft_payload, factory)
    for actor in actors[1:3]:
        assert (
            api.post(
                f"/api/v1/drops/{drop_id}/entries", json={}, headers=headers(actor)
            ).status_code
            == 201
        )
    # Later revocation does not subtract a committed accepted identity.
    with factory.begin() as db:
        grant = db.scalar(
            select(m.EligibilityGrant).where(m.EligibilityGrant.user_id == actors[1].id)
        )
        grant.revoked_at = db_now(db)
    close_due(api, actors, factory, drop_id)
    path = f"/api/v1/admin/drops/{drop_id}/draw"
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(
            pool.map(lambda _: api.post(path, json={}, headers=headers(actors[0])), range(8))
        )
    assert all(r.status_code == 202 for r in results)
    assert len({r.json()["draw_id"] for r in results}) == 1
    with ThreadPoolExecutor(max_workers=4) as pool:
        ids = list(pool.map(lambda _: draw.compute_draw(UUID(drop_id), factory), range(8)))
    assert len(set(ids)) == 1
    with factory() as db:
        drop = db.get(m.Drop, UUID(drop_id))
        run = db.scalar(select(m.DrawRun))
        frozen = list(db.scalars(select(m.FrozenEntry)))
        ranks = list(db.scalars(select(m.DrawRank).order_by(m.DrawRank.rank)))
        seed = reveal_seed(drop.id, drop.encrypted_seed)
        assert len(seed) == 32 and hashlib.sha256(seed).hexdigest() == drop.seed_commitment
        canonical = b"".join((v + "\n").encode() for v in sorted(e.public_entry_id for e in frozen))
        assert canonical == manifest_bytes([e.public_entry_id for e in reversed(frozen)])
        assert hashlib.sha256(canonical).hexdigest() == run.manifest_commitment
        expected = sorted(
            (
                hmac.new(
                    seed, f"fair-drop:v1:{drop.id}:{e.public_entry_id}".encode(), hashlib.sha256
                ).digest(),
                e.public_entry_id,
                e.entry_id,
            )
            for e in frozen
        )
        assert [r.entry_id for r in ranks] == [e[2] for e in expected]
        assert [r.score_bytes for r in ranks] == [e[0] for e in expected]
        assert [r.rank for r in ranks] == [1, 2]
        assert run.processed_entries == run.total_entries == 2
    for statement in (
        "UPDATE frozen_entries SET public_entry_id='tampered'",
        "DELETE FROM draw_ranks",
        "UPDATE draw_runs SET manifest_commitment='tampered'",
        "UPDATE draw_runs SET status='COMPUTING'",
    ):
        with pytest.raises(DBAPIError):
            with factory.begin() as db:
                db.execute(text(statement))


def test_interrupted_publication_rolls_back_complete_ranking(
    api, actors, draft_payload, factory, monkeypatch
):
    drop_id = prepare_open(api, actors, draft_payload, factory)
    api.post(f"/api/v1/drops/{drop_id}/entries", json={}, headers=headers(actors[1]))
    close_due(api, actors, factory, drop_id)
    real_record = draw.record
    with factory() as db:
        original_seed = db.get(m.Drop, UUID(drop_id)).encrypted_seed
        original_run = db.scalar(select(m.DrawRun.id))

    def fail(*args, **kwargs):
        if args[2] == "RANKING_PUBLISHED":
            raise RuntimeError("simulated interruption before commit")
        return real_record(*args, **kwargs)

    monkeypatch.setattr(draw, "record", fail)
    with pytest.raises(RuntimeError):
        draw.compute_draw(UUID(drop_id), factory)
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(m.DrawRank)) == 0
        assert db.get(m.DrawRun, original_run).status == "COMPUTING"
    monkeypatch.setattr(draw, "record", real_record)
    assert draw.compute_draw(UUID(drop_id), factory) == original_run
    with factory() as db:
        assert db.get(m.Drop, UUID(drop_id)).encrypted_seed == original_seed
        assert db.get(m.DrawRun, original_run).status == "PUBLISHED"


def test_empty_ranking_has_empty_manifest(api, actors, draft_payload, factory):
    drop_id = prepare_open(api, actors, draft_payload, factory)
    close_due(api, actors, factory, drop_id)
    draw.compute_draw(UUID(drop_id), factory)
    with factory() as db:
        run = db.scalar(select(m.DrawRun))
        assert run.manifest_commitment == hashlib.sha256(b"").hexdigest()
        assert run.total_entries == run.processed_entries == 0
        assert run.status == "PUBLISHED"
