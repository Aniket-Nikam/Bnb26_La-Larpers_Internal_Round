import copy
import json
import subprocess
from uuid import UUID

import pytest

from app.allocation import lifecycle
from app.audit.verifier import verify

from .conftest import headers, prepare_open
from .test_draw import close_due


def test_pending_reveal_independent_verifier_privacy_and_compression(
    api, actors, draft_payload, factory, tmp_path
):
    drop_id = prepare_open(api, actors, draft_payload, factory)
    path = f"/api/v1/drops/{drop_id}/proof"
    pending = api.get(path).json()
    assert pending["status"] == "pending"
    assert "seed" not in pending and "entries" not in pending
    entry = api.post(f"/api/v1/drops/{drop_id}/entries", json={}, headers=headers(actors[1])).json()
    api.post(f"/api/v1/drops/{drop_id}/entries", json={}, headers=headers(actors[2]))
    close_due(api, actors, factory, drop_id)
    closed = api.get(path).json()
    assert closed["status"] == "pending" and closed["manifest_commitment"] is not None
    assert "seed" not in closed
    assert lifecycle.tick(factory) == []
    response = api.get(path, headers={"Accept-Encoding": "gzip"})
    proof = response.json()
    assert proof["status"] == "published"
    assert verify(proof, entry["public_entry_id"])["ranking_reproduced"]
    assert verify(proof)["inclusion_checked"] is False
    for actor in actors:
        assert str(actor.id) not in response.text
        assert actor.display_name not in response.text
        assert actor.public_id not in response.text
    assert "receipt_id" not in response.text and "encrypted_seed" not in response.text
    api.patch(
        f"/api/v1/admin/drops/{drop_id}",
        json={"description": "Detailed description. " * 100},
        headers=headers(actors[0]),
    )
    compressed = api.get(f"/api/v1/drops/{drop_id}", headers={"Accept-Encoding": "gzip"})
    assert compressed.headers["Content-Encoding"] == "gzip"
    # CLI is independently usable from standard Python; no application packages required.
    path = tmp_path / "proof.json"
    path.write_text(json.dumps(proof))
    result = subprocess.run(
        [
            "/usr/bin/python",
            "app/audit/verifier.py",
            str(path),
            "--public-entry-id",
            entry["public_entry_id"],
        ],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0 and json.loads(result.stdout)["valid"]
    export = api.get(f"/api/v1/admin/drops/{drop_id}/entries/export", headers=headers(actors[0]))
    assert export.status_code == 200
    assert export.headers["Content-Type"].startswith("text/csv")
    assert export.text.startswith("public_entry_id,status,rank")
    assert actors[1].display_name not in export.text and str(actors[1].id) not in export.text
    for field, value in [
        ("seed", "0" * 64),
        ("manifest_commitment", "0" * 64),
        ("seed_commitment", "0" * 64),
    ]:
        altered = copy.deepcopy(proof)
        altered[field] = value
        with pytest.raises(ValueError):
            verify(altered)
    altered = copy.deepcopy(proof)
    altered["entries"][0]["rank"] = 2
    with pytest.raises(ValueError):
        verify(altered)
    altered = copy.deepcopy(proof)
    altered["entries"][0]["score_hex"] = "0" * 64
    with pytest.raises(ValueError):
        verify(altered)
    with pytest.raises(ValueError):
        verify(proof, "absent-participant")


def test_request_pattern_independence_and_canonical_vectors():
    import hashlib
    import hmac
    from types import SimpleNamespace

    from app.allocation.crypto import manifest_commitment
    from app.allocation.draw import calculate_ranking

    seed = bytes(range(32))
    drop = UUID("20000000-0000-4000-8000-000000000001")
    ids = ["fd_alpha", "fd_beta", "fd_gamma"]
    frozen = [SimpleNamespace(entry_id=n, public_entry_id=value) for n, value in enumerate(ids)]
    baseline = calculate_ranking("LOTTERY", seed, drop, frozen)
    for pattern in (list(reversed(frozen)), [frozen[2], frozen[0], frozen[1]], frozen):
        assert calculate_ranking("LOTTERY", seed, drop, pattern) == baseline
        assert (
            manifest_commitment([r.public_entry_id for r in pattern])
            == hashlib.sha256(b"fd_alpha\nfd_beta\nfd_gamma\n").hexdigest()
        )
    # Independent byte-level score vector, unaffected by request counts/arrival metadata.
    for row in baseline:
        assert (
            row[2]
            == hmac.new(
                seed,
                b"fair-drop:v1:20000000-0000-4000-8000-000000000001:" + row[1].encode(),
                hashlib.sha256,
            ).digest()
        )
