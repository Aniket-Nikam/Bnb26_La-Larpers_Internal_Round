from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.allocation.crypto import reveal_seed
from app.core import schemas as s
from app.core.clock import db_now
from app.core.config import get_settings
from app.drops.service import not_found
from app.persistence import models as m
from app.persistence.database import get_db

router = APIRouter(tags=["proof"])


@router.get("/drops/{drop_id}/proof", response_model=s.ProofResponse)
def proof(drop_id: UUID, db=Depends(get_db)):
    drop = db.get(m.Drop, drop_id)
    if (
        drop is None
        or drop.phase == "DRAFT"
        or (drop.mode == "FCFS_DEMO" and get_settings().app_profile != "demo")
    ):
        not_found()
    run = db.scalar(select(m.DrawRun).where(m.DrawRun.drop_id == drop_id))
    if run is None or run.status != "PUBLISHED":
        return s.PendingProof(
            phase=drop.phase,
            seed_commitment=drop.seed_commitment,
            manifest_commitment=run.manifest_commitment if run else None,
            server_time=db_now(db),
        )
    rows = db.execute(
        select(m.FrozenEntry.public_entry_id, m.DrawRank.score_bytes, m.DrawRank.rank)
        .join(
            m.DrawRank,
            (m.DrawRank.draw_id == m.FrozenEntry.draw_id)
            & (m.DrawRank.entry_id == m.FrozenEntry.entry_id),
        )
        .where(m.FrozenEntry.draw_id == run.id)
        .order_by(m.DrawRank.rank)
    ).all()
    seed = reveal_seed(drop.id, drop.encrypted_seed) if drop.mode == "LOTTERY" else None
    return s.PublishedProof(
        drop_id=drop.id,
        draw_id=run.id,
        algorithm_version=run.algorithm_version,
        rules_version=drop.rules_version,
        mode=drop.mode,
        seed=seed.hex() if seed is not None else None,
        seed_commitment=drop.seed_commitment,
        manifest_commitment=run.manifest_commitment,
        entries=[
            s.ProofEntry(
                public_entry_id=r.public_entry_id,
                score_hex=r.score_bytes.hex() if r.score_bytes is not None else None,
                rank=r.rank,
            )
            for r in rows
        ],
        server_time=db_now(db),
    )
