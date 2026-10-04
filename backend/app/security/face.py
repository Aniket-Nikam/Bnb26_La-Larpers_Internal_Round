"""Facial recognition feature extraction and 1:N duplicate detection."""

import base64
import io
import re
from typing import Optional

import face_recognition
import numpy as np
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.persistence.models import User


def extract_face_embedding(image_data: str) -> list[float]:
    """Decode base64 image data and extract a 128-dimensional facial embedding vector."""
    if not image_data or not isinstance(image_data, str):
        raise DomainError(
            "VALIDATION_ERROR",
            "A camera face scan is required to register an account.",
            422,
        )

    # Strip Data URL prefix if present (e.g. data:image/jpeg;base64,...)
    cleaned = re.sub(r"^data:image/[a-zA-Z0-9.+-]+;base64,", "", image_data.strip())
    try:
        raw_bytes = base64.b64decode(cleaned, validate=True)
        img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
        image_np = np.array(img)
    except Exception:
        raise DomainError(
            "VALIDATION_ERROR",
            "Invalid image data received from camera scan.",
            422,
        ) from None

    # Detect face and extract 128-d embedding
    encodings = face_recognition.face_encodings(image_np)
    if len(encodings) == 0:
        raise DomainError(
            "VALIDATION_ERROR",
            "No face detected in scan. Ensure your face is centered, well-lit, and facing the camera.",
            422,
        )
    if len(encodings) > 1:
        raise DomainError(
            "VALIDATION_ERROR",
            "Multiple faces detected. Ensure only one person is in the camera frame.",
            422,
        )

    return encodings[0].tolist()


def check_duplicate_face(
    db: Session,
    new_embedding: list[float],
    threshold: float = 0.60,
) -> Optional[User]:
    """Check if the new embedding matches any existing user within Euclidean distance threshold.

    dlib's ResNet model achieves 99.38% LFW accuracy with distance < 0.60.
    """
    candidates = db.scalars(select(User).where(User.face_embedding.isnot(None))).all()
    if not candidates:
        return None

    new_vec = np.array(new_embedding, dtype=np.float64)
    for user in candidates:
        if not user.face_embedding:
            continue
        existing_vec = np.array(user.face_embedding, dtype=np.float64)
        distance = float(np.linalg.norm(existing_vec - new_vec))
        if distance < threshold:
            return user

    return None
