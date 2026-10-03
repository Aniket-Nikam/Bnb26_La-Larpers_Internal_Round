from fastapi import APIRouter

from app.core.errors import DomainError
from app.core.schemas import ProfilePatch, ProfileResponse, SessionInput, SessionResponse

router = APIRouter(tags=["security"])


def unavailable():
    raise DomainError("NOT_IMPLEMENTED", "Security endpoint awaits Member 2.", 501)


@router.post("/auth/session", response_model=SessionResponse)
def login(body: SessionInput):
    unavailable()


@router.get("/auth/me", response_model=SessionResponse)
def me():
    unavailable()


@router.delete("/auth/session", status_code=204)
def logout():
    unavailable()


@router.patch("/profile", response_model=ProfileResponse)
def profile(body: ProfilePatch):
    unavailable()
