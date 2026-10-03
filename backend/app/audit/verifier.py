"""Independent bounded verifier: standard library only, no database/backend crypto imports.
python -m app.audit.verifier proof.json [--public-entry-id fd_...] or proof from stdin '-'.
"""

import argparse
import hashlib
import hmac
import json
import re
import sys
from pathlib import Path
from uuid import UUID

PUBLIC_ID = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
HEX = re.compile(r"[0-9a-f]{64}\Z")
MAX_BYTES = 20_000_000


def verify(proof: dict, public_entry_id: str | None = None) -> dict:
    def require(condition, message):
        if not condition:
            raise ValueError(message)

    require(
        isinstance(proof, dict) and proof.get("status") == "published", "Proof is not published."
    )
    entries = proof.get("entries")
    require(isinstance(entries, list) and len(entries) <= 50000, "Invalid or oversized manifest.")
    try:
        drop_id = str(UUID(proof.get("drop_id", "")))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Invalid drop ID.") from None
    require(proof["drop_id"] == drop_id, "Drop ID must be canonical lowercase UUID text.")
    require(proof.get("rules_version") == "v1.0", "Unsupported rules version.")
    ids, ranks = [], []
    for entry in entries:
        require(isinstance(entry, dict), "Invalid manifest entry.")
        value, rank = entry.get("public_entry_id"), entry.get("rank")
        require(isinstance(value, str) and PUBLIC_ID.fullmatch(value), "Invalid public entry ID.")
        require(type(rank) is int and rank > 0, "Invalid rank.")
        ids.append(value)
        ranks.append(rank)
    require(len(set(ids)) == len(ids), "Duplicate public entry IDs.")
    require(sorted(ranks) == list(range(1, len(entries) + 1)), "Ranks are not unique and complete.")
    manifest = b"".join((value + "\n").encode("utf-8") for value in sorted(ids))
    require(
        hashlib.sha256(manifest).hexdigest() == proof.get("manifest_commitment"),
        "Manifest commitment mismatch.",
    )
    mode = proof.get("mode")
    reproduced = False
    if mode == "LOTTERY":
        require(
            proof.get("algorithm_version") == "hmac-sha256-v1", "Unsupported lottery algorithm."
        )
        seed_hex = proof.get("seed")
        require(isinstance(seed_hex, str) and HEX.fullmatch(seed_hex), "Invalid revealed seed.")
        seed = bytes.fromhex(seed_hex)
        require(
            hashlib.sha256(seed).hexdigest() == proof.get("seed_commitment"),
            "Seed commitment mismatch.",
        )
        calculated = []
        for entry in entries:
            value = entry["public_entry_id"]
            score = hmac.new(
                seed, f"fair-drop:v1:{drop_id}:{value}".encode("utf-8"), hashlib.sha256
            ).digest()
            require(score.hex() == entry.get("score_hex"), "Score mismatch.")
            calculated.append((score, value, entry["rank"]))
        require(
            [row[2] for row in sorted(calculated)] == list(range(1, len(entries) + 1)),
            "Rank ordering mismatch.",
        )
        reproduced = True
    elif mode == "FCFS_DEMO":
        require(
            proof.get("algorithm_version") == "fcfs-admission-v1", "Unsupported FCFS algorithm."
        )
        require(
            proof.get("seed") is None
            and proof.get("seed_commitment") is None
            and all(e.get("score_hex") is None for e in entries),
            "FCFS must not claim HMAC lottery evidence.",
        )
    else:
        raise ValueError("Unsupported allocation mode.")
    if public_entry_id is not None:
        require(public_entry_id in set(ids), "Participant entry is absent from the manifest.")
    return {
        "valid": True,
        "entry_count": len(entries),
        "mode": mode,
        "ranking_reproduced": reproduced,
        "inclusion_checked": public_entry_id is not None,
        "limitations": [
            "Commit/reveal does not prevent operator seed-search or selective cancellation."
        ]
        + (
            []
            if reproduced
            else ["FCFS manifest checks do not independently establish admission order."]
        ),
    }


def main():
    parser = argparse.ArgumentParser(description="Verify a FairDrop public proof")
    parser.add_argument("proof", help="JSON proof file, or - for stdin")
    parser.add_argument("--public-entry-id")
    args = parser.parse_args()
    try:
        if args.proof == "-":
            data = sys.stdin.buffer.read(MAX_BYTES + 1)
        else:
            with Path(args.proof).open("rb") as stream:
                data = stream.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError("Proof exceeds verifier size limit.")
        result = verify(json.loads(data), args.public_entry_id)
        print(json.dumps(result))
        return 0
    except (OSError, ValueError, TypeError, KeyError):
        # Do not echo raw file contents/exception input; caller receives an honest failure.
        print(json.dumps({"valid": False, "message": "Proof validation failed."}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
