import json
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from pydantic import TypeAdapter
from sqlalchemy import inspect

from app.core import schemas as s
from app.main import app
from app.persistence.database import get_engine


def test_schema_tables_and_partial_indexes():
    inspector = inspect(get_engine())
    assert len(inspector.get_table_names()) == 15  # 14 records + alembic_version
    indexes = inspector.get_indexes("reservations")
    assert {i["name"] for i in indexes} >= {"uq_active_user", "uq_active_slot"}
    assert len(inspector.get_foreign_keys("reservations")) == 4


def test_contract_routes_error_envelope_and_health():
    with TestClient(app) as client:
        request_id = str(uuid4())
        response = client.get("/api/health/live", headers={"X-Request-ID": request_id})
        assert response.json() == {"status": "alive"}
        assert response.headers["X-Request-ID"] == request_id
        assert (
            client.post("/api/v1/auth/session", json={"access_code": "secret"}).json()["error"][
                "code"
            ]
            == "CSRF_REJECTED"
        )
        response = client.post(
            "/api/v1/auth/session", json={"access_code": "secret", "role": "admin"}
        )
        assert response.status_code == 422
        assert "secret" not in response.text
        ready = client.get("/api/health/ready")
        assert ready.status_code == 200
        assert ready.json()["capabilities"]["safe_reads"]
        assert ready.json()["dependencies"]["security"] == "ready"
        missing = client.get("/unknown")
        assert missing.json()["error"]["code"] == "NOT_FOUND"
        too_big = client.post("/api/v1/auth/session", content=b"a" * 65537)
        assert too_big.status_code == 413
    schema = app.openapi()
    assert len(schema["paths"]) == 31
    for route in ("/api/v1/profile", "/api/v1/admin/drops", "/api/v1/drops/{drop_id}/entries"):
        method = "patch" if route.endswith("profile") else "post"
        params = {p["name"] for p in schema["paths"][route][method]["parameters"]}
        assert params >= {"Origin", "X-CSRF-Token", "Idempotency-Key"}


def test_exported_examples_validate():
    examples = Path(__file__).resolve().parents[3] / "contracts" / "examples"
    for path in examples.glob("*.json"):
        data = json.loads(path.read_text())
        if path.name.startswith("error-"):
            s.ErrorResponse.model_validate(data)
        elif path.name.startswith("lab-"):
            s.RunDetail.model_validate(data)
        elif path.name.startswith("proof-"):
            TypeAdapter(s.ProofResponse).validate_python(data)
        elif path.name == "scheduled.json":
            s.DropDetail.model_validate(data)
        else:
            s.EntryState.model_validate(data)
    assert TypeAdapter(s.ProofResponse).json_schema()["discriminator"]
