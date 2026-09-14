import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

ALGORITHM = "HS256"
password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(subject: str, role: str | None = None) -> str:
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.access_token_expire_minutes,
    )
    payload = {"sub": subject, "exp": expires_at}
    if role is not None:
        payload["role"] = role
    return jwt.encode(
        payload,
        settings.auth_secret_key,
        algorithm=ALGORITHM,
    )


def decode_token_payload(token: str) -> dict:
    return jwt.decode(
        token,
        settings.auth_secret_key,
        algorithms=[ALGORITHM],
    )


def decode_access_token(token: str) -> str:
    payload = decode_token_payload(token)
    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise jwt.InvalidTokenError("Token subject is missing")
    return subject


def generate_password_reset_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

