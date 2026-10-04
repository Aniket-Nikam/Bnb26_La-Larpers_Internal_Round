"""Face feature extraction and 1:N duplicate-account detection."""

import base64
import io
import re

import face_recognition
import numpy as np
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.persistence.models import User


def extract_face_embedding(image_data: str) -> list[float]:
    """Decode a camera image and return its 128-dimensional face embedding."""
    if not image_data or not isinstance(image_data, str):
        raise DomainError(
            "VALIDATION_ERROR",
            "A camera face scan is required to register an account.",
            422,
        )
    cleaned = re.sub(r"^data:image/[a-zA-Z0-9.+-]+;base64,", "", image_data.strip())
    try:
        raw_bytes = base64.b64decode(cleaned, validate=True)
        image = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
        image_array = np.array(image)
    except Exception:
        raise DomainError(
            "VALIDATION_ERROR",
            "Invalid image data received from the camera scan.",
            422,
        ) from None

    encodings = face_recognition.face_encodings(image_array)
    if not encodings:
        raise DomainError(
            "VALIDATION_ERROR",
            "No face detected. Face the camera in even lighting and try again.",
            422,
        )
    if len(encodings) > 1:
        raise DomainError(
            "VALIDATION_ERROR",
            "Multiple faces detected. Keep only one person in the frame.",
            422,
        )
    return encodings[0].tolist()


def check_duplicate_face(
    db: Session, new_embedding: list[float], threshold: float = 0.60
) -> User | None:
    """Return the first existing account within the configured face distance."""
    candidates = db.scalars(select(User).where(User.face_embedding.isnot(None))).all()
    new_vector = np.array(new_embedding, dtype=np.float64)
    for user in candidates:
        if not user.face_embedding:
            continue
        existing_vector = np.array(user.face_embedding, dtype=np.float64)
        if float(np.linalg.norm(existing_vector - new_vector)) < threshold:
            return user
    return None
