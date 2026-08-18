from fastapi.testclient import TestClient

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
ME_URL = "/api/v1/auth/me"

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
