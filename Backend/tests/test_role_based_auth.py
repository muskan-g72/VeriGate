import uuid
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.audit_log import AuditLog
from app.models.user import User

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
ME_URL = "/api/v1/auth/me"
ADMIN_STATS_URL = "/api/v1/admin/statistics"
ADMIN_USERS_URL = "/api/v1/admin/users"


def create_user_in_db(
    db_session: Session,
    email: str,
    password: str = "SecurePassword123!",
    role: str = "user",
    is_active: bool = True,
) -> User:
    user = User(
        email=email.lower(),
        password_hash=hash_password(password),
        full_name="Test Account",
        system_role=role,
        is_active=is_active,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_user_registration_defaults_to_user_role(client: TestClient) -> None:
    unique_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    response = client.post(
        REGISTER_URL,
        json={
            "email": unique_email,
            "password": "SecurePassword123!",
            "full_name": "Standard User",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["role"] == "user"
    assert data["system_role"] == "user"


def test_normal_user_login_and_me(client: TestClient, db_session: Session) -> None:
    unique_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    create_user_in_db(db_session, email=unique_email, role="user")

    # Login
    login_resp = client.post(
        LOGIN_URL,
        data={"username": unique_email, "password": "SecurePassword123!"},
    )
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    assert "access_token" in token_data
    assert token_data["role"] == "user"

    # /me endpoint
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    me_resp = client.get(ME_URL, headers=headers)
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == unique_email
    assert me_data["role"] == "user"


def test_normal_user_denied_admin_endpoints(
    client: TestClient, db_session: Session
) -> None:
    unique_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    create_user_in_db(db_session, email=unique_email, role="user")

    login_resp = client.post(
        LOGIN_URL,
        data={"username": unique_email, "password": "SecurePassword123!"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Accessing admin stats must return 403 Forbidden
    resp_stats = client.get(ADMIN_STATS_URL, headers=headers)
    assert resp_stats.status_code == 403
    assert resp_stats.json()["detail"] == "Admin access required"

    # Accessing admin users list must return 403 Forbidden
    resp_users = client.get(ADMIN_USERS_URL, headers=headers)
    assert resp_users.status_code == 403
    assert resp_users.json()["detail"] == "Admin access required"


def test_admin_user_can_access_admin_endpoints(
    client: TestClient, db_session: Session
) -> None:
    admin_email = f"admin_{uuid.uuid4().hex[:8]}@example.com"
    create_user_in_db(db_session, email=admin_email, role="admin")

    login_resp = client.post(
        LOGIN_URL,
        data={"username": admin_email, "password": "SecurePassword123!"},
    )
    assert login_resp.status_code == 200
    assert login_resp.json()["role"] == "admin"
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Access stats
    resp_stats = client.get(ADMIN_STATS_URL, headers=headers)
    assert resp_stats.status_code == 200
    data = resp_stats.json()
    assert "total_users" in data
    assert "successful_verification_runs" in data

    # Access users
    resp_users = client.get(ADMIN_USERS_URL, headers=headers)
    assert resp_users.status_code == 200
    assert isinstance(resp_users.json(), list)


def test_admin_can_promote_and_demote_user(
    client: TestClient, db_session: Session
) -> None:
    admin_email = f"admin_{uuid.uuid4().hex[:8]}@example.com"
    admin_user = create_user_in_db(db_session, email=admin_email, role="admin")

    target_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    target_user = create_user_in_db(db_session, email=target_email, role="user")

    login_resp = client.post(
        LOGIN_URL,
        data={"username": admin_email, "password": "SecurePassword123!"},
    )
    headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    # Promote target user to admin
    promote_resp = client.patch(
        f"{ADMIN_USERS_URL}/{target_user.id}/role",
        headers=headers,
        json={"role": "admin"},
    )
    assert promote_resp.status_code == 200
    assert promote_resp.json()["role"] == "admin"

    # Demote target user back to user
    demote_resp = client.patch(
        f"{ADMIN_USERS_URL}/{target_user.id}/role",
        headers=headers,
        json={"role": "user"},
    )
    assert demote_resp.status_code == 200
    assert demote_resp.json()["role"] == "user"


def test_admin_cannot_demote_self(
    client: TestClient, db_session: Session
) -> None:
    admin_email = f"admin_{uuid.uuid4().hex[:8]}@example.com"
    admin_user = create_user_in_db(db_session, email=admin_email, role="admin")

    login_resp = client.post(
        LOGIN_URL,
        data={"username": admin_email, "password": "SecurePassword123!"},
    )
    headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    # Self demotion attempt must return 400
    self_demote = client.patch(
        f"{ADMIN_USERS_URL}/{admin_user.id}/role",
        headers=headers,
        json={"role": "user"},
    )
    assert self_demote.status_code == 400
    assert "cannot demote your own" in self_demote.json()["detail"].lower()


def test_admin_can_toggle_user_status_and_not_self(
    client: TestClient, db_session: Session
) -> None:
    admin_email = f"admin_{uuid.uuid4().hex[:8]}@example.com"
    admin_user = create_user_in_db(db_session, email=admin_email, role="admin")

    target_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    target_user = create_user_in_db(db_session, email=target_email, role="user")

    login_resp = client.post(
        LOGIN_URL,
        data={"username": admin_email, "password": "SecurePassword123!"},
    )
    headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    # Disable target user
    disable_resp = client.patch(
        f"{ADMIN_USERS_URL}/{target_user.id}/status",
        headers=headers,
        json={"is_active": False},
    )
    assert disable_resp.status_code == 200
    assert disable_resp.json()["is_active"] is False

    # Self-deactivation attempt must return 400
    self_disable = client.patch(
        f"{ADMIN_USERS_URL}/{admin_user.id}/status",
        headers=headers,
        json={"is_active": False},
    )
    assert self_disable.status_code == 400
    assert "cannot deactivate your own" in self_disable.json()["detail"].lower()


def test_login_and_failed_login_audit_logs(
    client: TestClient, db_session: Session
) -> None:
    email = f"audit_user_{uuid.uuid4().hex[:8]}@example.com"
    create_user_in_db(db_session, email=email, role="user")

    # Failed login
    client.post(LOGIN_URL, data={"username": email, "password": "WrongPassword!"})

    failed_log = db_session.scalar(
        select(AuditLog)
        .where(AuditLog.action == "failed_login")
        .order_by(AuditLog.created_at.desc())
    )
    assert failed_log is not None
    assert email in (failed_log.description or "")

    # Successful login
    client.post(LOGIN_URL, data={"username": email, "password": "SecurePassword123!"})

    success_log = db_session.scalar(
        select(AuditLog)
        .where(AuditLog.action == "login")
        .order_by(AuditLog.created_at.desc())
    )
    assert success_log is not None
    assert email in (success_log.description or "")
