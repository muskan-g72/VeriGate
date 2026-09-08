from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.security import hash_token
from app.models.password_reset_token import PasswordResetToken
from sqlalchemy.orm import Session

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
ME_URL = "/api/v1/auth/me"
FORGOT_PASSWORD_URL = "/api/v1/auth/forgot-password"
RESET_PASSWORD_URL = "/api/v1/auth/reset-password"

USER_PAYLOAD = {
    "email": "test.user@example.com",
    "password": "StrongPassword123!",
    "full_name": "Test User",
}


def register_user(client: TestClient) -> dict[str, object]:
    response = client.post(REGISTER_URL, json=USER_PAYLOAD)
    assert response.status_code == 201
    return response.json()


def login_user(client: TestClient) -> dict[str, str]:
    response = client.post(
        LOGIN_URL,
        data={
            "username": USER_PAYLOAD["email"],
            "password": USER_PAYLOAD["password"],
        },
    )
    assert response.status_code == 200
    return response.json()


def test_register_user(client: TestClient) -> None:
    user = register_user(client)

    assert user["email"] == USER_PAYLOAD["email"]
    assert user["full_name"] == USER_PAYLOAD["full_name"]
    assert user["is_active"] is True
    assert "id" in user
    assert "password" not in user
    assert "password_hash" not in user


def test_registration_normalizes_email(client: TestClient) -> None:
    payload = USER_PAYLOAD | {"email": "Test.User@Example.COM"}
    response = client.post(REGISTER_URL, json=payload)

    assert response.status_code == 201
    assert response.json()["email"] == "test.user@example.com"


def test_registration_rejects_short_password(client: TestClient) -> None:
    payload = USER_PAYLOAD | {"password": "short"}
    response = client.post(REGISTER_URL, json=payload)

    assert response.status_code == 422


def test_duplicate_email_returns_conflict(client: TestClient) -> None:
    register_user(client)
    response = client.post(REGISTER_URL, json=USER_PAYLOAD)

    assert response.status_code == 409
    assert response.json()["detail"] == "A user with this email already exists"


def test_login_returns_bearer_token(client: TestClient) -> None:
    register_user(client)
    token = login_user(client)

    assert token["token_type"] == "bearer"
    assert token["access_token"]


def test_login_rejects_wrong_password(client: TestClient) -> None:
    register_user(client)
    response = client.post(
        LOGIN_URL,
        data={
            "username": USER_PAYLOAD["email"],
            "password": "IncorrectPassword123!",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_me_returns_authenticated_user(client: TestClient) -> None:
    registered_user = register_user(client)
    token = login_user(client)

    response = client.get(
        ME_URL,
        headers={"Authorization": f"Bearer {token['access_token']}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == registered_user["id"]
    assert response.json()["email"] == USER_PAYLOAD["email"]


def test_me_requires_token(client: TestClient) -> None:
    response = client.get(ME_URL)

    assert response.status_code == 401


def test_me_rejects_invalid_token(client: TestClient) -> None:
    response = client.get(
        ME_URL,
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


def test_forgot_password_unknown_email_returns_generic_message(
    client: TestClient,
) -> None:
    with patch("app.api.routes.auth.send_password_reset_email") as mock_email:
        response = client.post(
            FORGOT_PASSWORD_URL,
            json={"email": "nonexistent@example.com"},
        )

    assert response.status_code == 200
    assert "If an account exists" in response.json()["message"]
    mock_email.assert_not_called()


def test_forgot_password_valid_user_creates_token_and_sends_email(
    client: TestClient,
    db_session: Session,
) -> None:
    register_user(client)

    with patch("app.api.routes.auth.send_password_reset_email") as mock_email:
        response = client.post(
            FORGOT_PASSWORD_URL,
            json={"email": USER_PAYLOAD["email"]},
        )

    assert response.status_code == 200
    assert "If an account exists" in response.json()["message"]
    mock_email.assert_called_once()
    to_email, reset_link = mock_email.call_args[0]
    assert to_email == USER_PAYLOAD["email"]
    assert "token=" in reset_link

    # Verify only hash is stored in the database, never the raw token
    raw_token = reset_link.split("token=")[1]
    tokens = db_session.scalars(select(PasswordResetToken)).all()
    assert len(tokens) == 1
    assert tokens[0].token_hash == hash_token(raw_token)
    assert tokens[0].token_hash != raw_token
    token_expires = tokens[0].expires_at
    if token_expires.tzinfo is None:
        token_expires = token_expires.replace(tzinfo=UTC)
    assert token_expires > datetime.now(UTC)


def test_forgot_password_invalidates_previous_unused_tokens(
    client: TestClient,
    db_session: Session,
) -> None:
    register_user(client)

    with patch("app.api.routes.auth.send_password_reset_email") as mock_email:
        client.post(FORGOT_PASSWORD_URL, json={"email": USER_PAYLOAD["email"]})
        first_token = mock_email.call_args[0][1].split("token=")[1]

        client.post(FORGOT_PASSWORD_URL, json={"email": USER_PAYLOAD["email"]})
        second_token = mock_email.call_args[0][1].split("token=")[1]

    assert first_token != second_token

    tokens = db_session.scalars(
        select(PasswordResetToken).order_by(PasswordResetToken.created_at)
    ).all()
    assert len(tokens) == 2
    # First token was invalidated
    assert tokens[0].used_at is not None
    # Second token is still active
    assert tokens[1].used_at is None

    # First token cannot be used
    fail_response = client.post(
        RESET_PASSWORD_URL,
        json={"token": first_token, "password": "BrandNewPassword123!"},
    )
    assert fail_response.status_code == 400
    assert "already been used" in fail_response.json()["detail"]


def test_reset_password_success_and_login_flow(client: TestClient) -> None:
    register_user(client)

    with patch("app.api.routes.auth.send_password_reset_email") as mock_email:
        client.post(FORGOT_PASSWORD_URL, json={"email": USER_PAYLOAD["email"]})
        raw_token = mock_email.call_args[0][1].split("token=")[1]

    new_password = "CompletelyNewPassword456!"
    reset_response = client.post(
        RESET_PASSWORD_URL,
        json={"token": raw_token, "password": new_password},
    )
    assert reset_response.status_code == 200
    assert "successfully reset" in reset_response.json()["message"]

    # Old password no longer works
    old_login = client.post(
        LOGIN_URL,
        data={"username": USER_PAYLOAD["email"], "password": USER_PAYLOAD["password"]},
    )
    assert old_login.status_code == 401

    # New password works
    new_login = client.post(
        LOGIN_URL,
        data={"username": USER_PAYLOAD["email"], "password": new_password},
    )
    assert new_login.status_code == 200
    assert new_login.json()["access_token"]

    # Single-use: Reusing the same token fails
    reuse_response = client.post(
        RESET_PASSWORD_URL,
        json={"token": raw_token, "password": "YetAnotherPassword789!"},
    )
    assert reuse_response.status_code == 400
    assert "already been used" in reuse_response.json()["detail"]


def test_reset_password_invalid_token(client: TestClient) -> None:
    response = client.post(
        RESET_PASSWORD_URL,
        json={"token": "nonexistent-token-123", "password": "NewValidPassword123!"},
    )
    assert response.status_code == 400
    assert "Invalid or expired" in response.json()["detail"]


def test_reset_password_expired_token(
    client: TestClient,
    db_session: Session,
) -> None:
    register_user(client)

    with patch("app.api.routes.auth.send_password_reset_email") as mock_email:
        client.post(FORGOT_PASSWORD_URL, json={"email": USER_PAYLOAD["email"]})
        raw_token = mock_email.call_args[0][1].split("token=")[1]

    # Force expiration in database
    token_record = db_session.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == hash_token(raw_token)
        )
    )
    assert token_record is not None
    token_record.expires_at = datetime.now(UTC) - timedelta(minutes=5)
    db_session.commit()

    response = client.post(
        RESET_PASSWORD_URL,
        json={"token": raw_token, "password": "NewValidPassword123!"},
    )
    assert response.status_code == 400
    assert "has expired" in response.json()["detail"]


def test_reset_password_rejects_short_password(client: TestClient) -> None:
    response = client.post(
        RESET_PASSWORD_URL,
        json={"token": "valid-looking-token", "password": "short"},
    )
    assert response.status_code == 422

