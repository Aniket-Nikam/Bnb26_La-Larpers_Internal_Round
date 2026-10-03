"""Run from backend: uv run python -m app.core.export_contract."""

import json
from pathlib import Path

from app.main import app


def main():
    target = Path(__file__).resolve().parents[3] / "contracts"
    target.mkdir(exist_ok=True)
    (target / "openapi.json").write_text(json.dumps(app.openapi(), indent=2) + "\n")
    (target / "version.txt").write_text("v1.0\n")
    print(f"Exported {len(app.openapi()['paths'])} paths to {target / 'openapi.json'}")


if __name__ == "__main__":
    main()
