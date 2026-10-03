from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


ALLOWED_PROFILE_FIELDS = {"display_name", "timezone"}


def validate_profile_patch(patch: dict[str, object]) -> tuple[str | None, str | None]:
    unexpected = set(patch) - ALLOWED_PROFILE_FIELDS
    if unexpected:
        raise ValueError(f"unsupported profile fields: {', '.join(sorted(unexpected))}")
    if not patch:
        raise ValueError("at least one profile field is required")
    display_name: str | None = None
    timezone: str | None = None
    if "display_name" in patch:
        value = patch["display_name"]
        if not isinstance(value, str):
            raise ValueError("display_name must be a string")
        value = " ".join(value.strip().split())
        if not 1 <= len(value) <= 100 or any(ord(character) < 32 for character in value):
            raise ValueError("display_name must contain 1 to 100 printable characters")
        display_name = value
    if "timezone" in patch:
        value = patch["timezone"]
        if not isinstance(value, str) or not 1 <= len(value) <= 64:
            raise ValueError("timezone must be a valid IANA timezone")
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("timezone must be a valid IANA timezone") from exc
        timezone = value
    return display_name, timezone
