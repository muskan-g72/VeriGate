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


def create_access_token(subject: str) -> str:
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.access_token_expire_minutes,
    )
    return jwt.encode(
        {"sub": subject, "exp": expires_at},
        settings.auth_secret_key,
        algorithm=ALGORITHM,
    )


def decode_access_token(token: str) -> str:
    payload = jwt.decode(
        token,
        settings.auth_secret_key,
        algorithms=[ALGORITHM],
    )
    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise jwt.InvalidTokenError("Token subject is missing")
    return subject
