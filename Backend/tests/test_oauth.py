from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.oauth_account import OAuthAccount
from app.models.user import User


class ProviderResponse:
    def __init__(self, payload): self.payload = payload
    def raise_for_status(self): return None
    def json(self): return self.payload


class ProviderClient:
    async def __aenter__(self): return self
    async def __aexit__(self, *_): return None
    async def post(self, *_args, **_kwargs): return ProviderResponse({"access_token": "provider-token"})
    async def get(self, url, **_kwargs):
        if url.endswith("/user/emails"):
            return ProviderResponse([{"email": "oauth@example.com", "primary": True, "verified": True}])
        return ProviderResponse({"sub": "google-123", "email": "oauth@example.com", "email_verified": True, "name": "OAuth User"})


def configure_oauth(monkeypatch):
    monkeypatch.setattr("app.api.routes.auth.settings.google_client_id", "google-client")
    monkeypatch.setattr("app.api.routes.auth.settings.google_client_secret", "google-secret")
    monkeypatch.setattr("app.api.routes.auth.settings.frontend_url", "http://frontend.test")
    monkeypatch.setattr("app.api.routes.auth.httpx.AsyncClient", lambda **_: ProviderClient())


def begin(client: TestClient) -> str:
    response = client.get("/api/v1/auth/google/login", follow_redirects=False)
    assert response.status_code == 307
    return parse_qs(urlparse(response.headers["location"]).query)["state"][0]


def callback(client: TestClient, state: str):
    return client.get(f"/api/v1/auth/google/callback?code=provider-code&state={state}", follow_redirects=False)


def test_oauth_creates_non_admin_user_and_exchanges_once(client: TestClient, db_session: Session, monkeypatch):
    configure_oauth(monkeypatch)
    response = callback(client, begin(client))
    assert response.status_code == 307
    code = parse_qs(urlparse(response.headers["location"]).query)["code"][0]
    token = client.post("/api/v1/auth/oauth/exchange", json={"code": code})
    assert token.status_code == 200
    assert client.post("/api/v1/auth/oauth/exchange", json={"code": code}).status_code == 400
    user = db_session.scalar(select(User).where(User.email == "oauth@example.com"))
    assert user and user.system_role == "user" and user.password_hash is None


def test_oauth_existing_account_logs_in_without_duplicate(client: TestClient, db_session: Session, monkeypatch):
    configure_oauth(monkeypatch)
    callback(client, begin(client)); callback(client, begin(client))
    assert len(db_session.scalars(select(OAuthAccount)).all()) == 1


def test_oauth_links_verified_email_to_existing_user(client: TestClient, db_session: Session, monkeypatch):
    configure_oauth(monkeypatch)
    user = User(email="oauth@example.com", password_hash=hash_password("Password123!"), system_role="user")
    db_session.add(user); db_session.commit()
    assert callback(client, begin(client)).status_code == 307
    account = db_session.scalar(select(OAuthAccount))
    assert account and account.user_id == user.id


def test_oauth_rejects_unverified_email(client: TestClient, monkeypatch):
    configure_oauth(monkeypatch)
    class UnverifiedClient(ProviderClient):
        async def get(self, *_args, **_kwargs): return ProviderResponse({"sub": "google-123", "email": "oauth@example.com", "email_verified": False})
    monkeypatch.setattr("app.api.routes.auth.httpx.AsyncClient", lambda **_: UnverifiedClient())
    response = callback(client, begin(client))
    assert response.status_code == 400


def test_oauth_rejects_invalid_state_and_password_login_for_oauth_user(client: TestClient, db_session: Session, monkeypatch):
    configure_oauth(monkeypatch)
    assert callback(client, "bad-state").status_code == 400
    db_session.add(User(email="only-oauth@example.com", password_hash=None, system_role="user")); db_session.commit()
    response = client.post("/api/v1/auth/login", data={"username": "only-oauth@example.com", "password": "Password123!"})
    assert response.status_code == 401
    assert "OAuth" in response.json()["detail"]
