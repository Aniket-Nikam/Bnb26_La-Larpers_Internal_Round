from uuid import UUID

from fastapi import APIRouter

from app.core.errors import DomainError
from app.core.schemas import ProofResponse

router = APIRouter(tags=["proof"])


@router.get("/drops/{drop_id}/proof", response_model=ProofResponse)
def proof(drop_id: UUID):
    raise DomainError("NOT_IMPLEMENTED", "Proof endpoint is not yet implemented.", 501)
