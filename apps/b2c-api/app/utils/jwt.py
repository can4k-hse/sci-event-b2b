from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.config import get_settings

settings = get_settings()


def create_access_token(subject: int | str, extra: dict[str, Any] | None = None) -> tuple[str, int]:
    now = datetime.now(tz=timezone.utc)
    expire_seconds = settings.access_token_expire_minutes * 60
    expire = now + timedelta(seconds=expire_seconds)

    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
        "type": "access",
    }
    if extra:
        payload.update(extra)

    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, expire_seconds


def decode_access_token(token: str) -> dict[str, Any]:
    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Token type mismatch")
    return payload
