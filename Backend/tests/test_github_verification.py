import asyncio
import hashlib
import hmac
import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.models.test_case import TestCase
from app.models.verification_run import VerificationRun
from app.services.automated_verification import sync_verification_run_status
from app.services.github_service import verify_github_signature, post_github_commit_status
from app.services.github_pr_verifier import run_github_pr_verification


def authenticated_headers(client: TestClient, email: str) -> dict[str, str]:
    password = "StrongPassword123!"
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "GitHub Test User"},
    )
    assert reg.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def sign_payload(payload_bytes: bytes, secret: str) -> str:
    signature = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={signature}"


def test_verify_github_signature_unit():
    secret = "my-secret-token"
    payload = b'{"hello": "world"}'
    valid_sig = sign_payload(payload, secret)

    assert verify_github_signature(payload, valid_sig, secret) is True
    assert verify_github_signature(payload, "sha256=invalid", secret) is False
    assert verify_github_signature(payload, None, secret) is False
    assert verify_github_signature(payload, "not-sha256-prefixed", secret) is False
    assert verify_github_signature(payload, valid_sig, "wrong-secret") is False

    from app.core.config import settings
    if settings.github_webhook_secret:
        env_sig = sign_payload(payload, settings.github_webhook_secret)
        assert verify_github_signature(payload, env_sig) is True


def test_post_github_commit_status_graceful_handling(monkeypatch):
    monkeypatch.setattr("app.services.github_service.settings.github_token", None)
    # Without token
    res = asyncio.run(
        post_github_commit_status(
            repo="muskan-g72/VeriGate",
            commit_sha="1234567890abcdef",
            state="success",
            target_url="https://verigate.app/run/1",
            description="Verification passed",
            token=None,
        )
    )
    assert res is False


def test_post_github_commit_status_uses_explicit_project_token(monkeypatch):
    monkeypatch.setattr("app.services.github_service.settings.github_token", None)
    captured = {}

    class Response:
        status_code = 201
        text = ""

    class Client:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, *_args, **kwargs):
            captured.update(kwargs)
            return Response()

    monkeypatch.setattr("app.services.github_service.httpx.AsyncClient", Client)
    result = asyncio.run(
        post_github_commit_status("owner/repo", "abc123", "success", "passed", token="project-token")
    )
    assert result is True
    assert captured["headers"]["Authorization"] == "Bearer project-token"


@pytest.mark.parametrize("status_code", [401, 403, 404, 422, 429])
def test_commit_status_preserves_github_http_failure(monkeypatch, status_code):
    class Response:
        text = '{"message":"write rejected"}'

        def __init__(self, code):
            self.status_code = code

    class Client:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, *_args, **_kwargs):
            return Response(status_code)

    monkeypatch.setattr("app.services.github_service.httpx.AsyncClient", Client)
    result = asyncio.run(
        post_github_commit_status(
            "owner/repo", "abc123", "success", "passed",
            token="fake-token", return_details=True,
        )
    )
    assert result[0] is False
    assert result[1] == status_code
    assert str(status_code) in result[2]


def test_github_webhook_ping(client: TestClient):
    resp = client.post(
        "/api/v1/github/webhook",
        headers={"X-GitHub-Event": "ping", "Content-Type": "application/json"},
        content=json.dumps({"zen": "Keep it logically awesome."}),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "pong"


def test_github_project_config_and_prs(client: TestClient):
    user_email = f"gh_user_{uuid.uuid4().hex[:8]}@example.com"
    headers = authenticated_headers(client, user_email)

    # Create project
    proj_resp = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "GitHub Integrated Project", "description": "Testing PR flow"},
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # Initial GitHub config (enabled by default)
    get_cfg = client.get(f"/api/v1/projects/{project_id}/github", headers=headers)
    assert get_cfg.status_code == 200
    cfg_data = get_cfg.json()
    assert cfg_data["github_verification_enabled"] is True
    assert cfg_data["github_repo"] is None

    # Update GitHub config
    patch_resp = client.patch(
        f"/api/v1/projects/{project_id}/github",
        headers=headers,
        json={
            "github_repo": "muskan-g72/VeriGate",
            "github_default_branch": "main",
            "github_verification_enabled": True,
            "github_webhook_secret": "test-webhook-secret-123",
            "github_token": "github_pat_project_only_token",
        },
    )
    assert patch_resp.status_code == 200
    updated_cfg = patch_resp.json()
    assert updated_cfg["github_repo"] == "muskan-g72/VeriGate"
    assert updated_cfg["github_verification_enabled"] is True
    assert updated_cfg["webhook_configured"] is True
    assert updated_cfg["token_configured"] is True
    assert "github_token" not in updated_cfg

    token_only = client.patch(
        f"/api/v1/projects/{project_id}/github",
        headers=headers,
        json={"github_token": "github_pat_replacement_token"},
    )
    assert token_only.status_code == 200
    assert token_only.json()["github_repo"] == "muskan-g72/VeriGate"
    assert token_only.json()["pr_comments_enabled"] is False
    assert updated_cfg["is_connected"] is True


def test_github_webhook_invalid_signatures(client: TestClient):
    user_email = f"gh_sig_{uuid.uuid4().hex[:8]}@example.com"
    headers = authenticated_headers(client, user_email)

    repo_name = f"muskan-g72/test-repo-{uuid.uuid4().hex[:6]}"

    # Create project with secret
    proj_resp = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "Sig Project"},
    )
    project_id = proj_resp.json()["id"]

    client.patch(
        f"/api/v1/projects/{project_id}/github",
        headers=headers,
        json={
            "github_repo": repo_name,
            "github_verification_enabled": True,
            "github_webhook_secret": "secure-secret-xyz",
        },
    )

    payload = {
        "action": "opened",
        "repository": {"full_name": repo_name},
        "pull_request": {
            "number": 10,
            "title": "Test PR",
            "html_url": f"https://github.com/{repo_name}/pull/10",
            "head": {"sha": "c0ffee123", "ref": "feat-branch"},
            "base": {"ref": "main"},
            "user": {"login": "octocat"},
        },
    }
    payload_bytes = json.dumps(payload).encode("utf-8")

    # Missing signature
    resp = client.post(
        "/api/v1/github/webhook",
        headers={"X-GitHub-Event": "pull_request", "Content-Type": "application/json"},
        content=payload_bytes,
    )
    assert resp.status_code == 401

    # Invalid signature
    resp = client.post(
        "/api/v1/github/webhook",
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": "sha256=wrongsignature",
            "Content-Type": "application/json",
        },
        content=payload_bytes,
    )
    assert resp.status_code == 401

    # Missing server secret -> 500 Internal Server Error
    from app.core.config import settings
    orig_global_secret = settings.github_webhook_secret
    try:
        settings.github_webhook_secret = None
        p_no_sec = client.post(
            "/api/v1/projects",
            headers=headers,
            json={"name": "No Sec Project"},
        ).json()["id"]
        repo_no_sec = f"org/no-sec-{uuid.uuid4().hex[:6]}"
        client.patch(
            f"/api/v1/projects/{p_no_sec}/github",
            headers=headers,
            json={"github_repo": repo_no_sec, "github_webhook_secret": ""},
        )
        p_bytes = json.dumps({
            "action": "opened",
            "repository": {"full_name": repo_no_sec},
            "pull_request": {"number": 1, "head": {"sha": "abc1234"}, "base": {"ref": "main"}},
        }).encode("utf-8")
        resp_no_sec = client.post(
            "/api/v1/github/webhook",
            headers={
                "X-GitHub-Event": "pull_request",
                "X-Hub-Signature-256": "sha256=abcdef123456",
                "Content-Type": "application/json",
            },
            content=p_bytes,
        )
        assert resp_no_sec.status_code == 500
        assert "Webhook secret not configured on server" in resp_no_sec.json()["detail"]
    finally:
        settings.github_webhook_secret = orig_global_secret


def test_github_webhook_pr_opened_and_idempotency(client: TestClient):
    user_email = f"gh_flow_{uuid.uuid4().hex[:8]}@example.com"
    headers = authenticated_headers(client, user_email)

    repo_name = f"org/repo-{uuid.uuid4().hex[:6]}"
    secret = "supersecret456"

    # Create project, suite, test case
    p_resp = client.post("/api/v1/projects", headers=headers, json={"name": "PR Test Project"})
    project_id = p_resp.json()["id"]

    client.patch(
        f"/api/v1/projects/{project_id}/github",
        headers=headers,
        json={
            "github_repo": repo_name,
            "github_verification_enabled": True,
            "github_webhook_secret": secret,
        },
    )

    s_resp = client.post(
        f"/api/v1/projects/{project_id}/test-suites",
        headers=headers,
        json={"name": "Automated Suite"},
    )
    suite_id = s_resp.json()["id"]

    tc_resp = client.post(
        f"/api/v1/test-suites/{suite_id}/test-cases",
        headers=headers,
        json={
            "title": "Verify PR Flow",
            "steps": "Check PR integration",
            "expected_result": "Success",
            "execution_mode": "automated",
            "automation_steps": [{"action": "goto", "value": "https://example.com"}],
        },
    )
    assert tc_resp.status_code == 201

    payload = {
        "action": "opened",
        "repository": {"full_name": repo_name},
        "pull_request": {
            "number": 99,
            "title": "Add Awesome Feature",
            "html_url": f"https://github.com/{repo_name}/pull/99",
            "head": {"sha": "deadbeef1234", "ref": "feature/awesome"},
            "base": {"ref": "main"},
            "user": {"login": "contributor1"},
        },
    }
    payload_bytes = json.dumps(payload).encode("utf-8")
    sig = sign_payload(payload_bytes, secret)

    # 1. First delivery -> 202 Accepted
    resp1 = client.post(
        "/api/v1/github/webhook",
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": sig,
            "Content-Type": "application/json",
        },
        content=payload_bytes,
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["status"] in ("queued", "enqueued")
    assert data1["pr_number"] == 99
    run_id = data1["run_id"]
    assert run_id is not None

    # 2. Duplicate delivery -> 200 OK (Idempotency)
    resp2 = client.post(
        "/api/v1/github/webhook",
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": sig,
            "Content-Type": "application/json",
        },
        content=payload_bytes,
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["duplicate"] is True
    assert data2["verification_run_id"] == run_id

    # 3. Verify PR run listed in project PRs endpoint and pr-verifications with project_id
    pr_verifs = client.get(f"/api/v1/github/pr-verifications?project_id={project_id}", headers=headers)
    assert pr_verifs.status_code == 200
    assert len(pr_verifs.json()) == 1
    assert pr_verifs.json()[0]["id"] == run_id

    proj_prs = client.get(f"/api/v1/projects/{project_id}/github/prs", headers=headers)
    assert proj_prs.status_code == 200
    prs_list = proj_prs.json()
    assert len(prs_list) == 1
    assert prs_list[0]["pr_number"] == 99
    assert prs_list[0]["trigger_source"] == "github_pr"
    assert prs_list[0]["pr_title"] == "Add Awesome Feature"
    assert prs_list[0]["pr_commit_sha"] == "deadbeef1234"
    assert prs_list[0]["pr_source_branch"] == "feature/awesome"
    assert prs_list[0]["pr_target_branch"] == "main"

    # 4. Verify PR run listed in global PR endpoint
    global_prs = client.get("/api/v1/github/pr-verifications", headers=headers)
    assert global_prs.status_code == 200
    g_list = global_prs.json()
    assert any(r["id"] == run_id for r in g_list)

    # 5. Verify VerificationRun details endpoint includes PR metadata
    run_detail = client.get(f"/api/v1/verification-runs/{run_id}", headers=headers)
    assert run_detail.status_code == 200
    run_obj = run_detail.json()
    assert run_obj["trigger_source"] == "github_pr"
    assert run_obj["pr_number"] == 99
    assert run_obj["pr_author"] == "contributor1"
    assert run_obj["pr_repository"] == repo_name

    # 6. Test synchronize action updates existing PR verification record
    sync_payload = {
        "action": "synchronize",
        "repository": {"full_name": repo_name},
        "pull_request": {
            "number": 99,
            "title": "Add Awesome Feature (Updated)",
            "html_url": f"https://github.com/{repo_name}/pull/99",
            "head": {"sha": "c0ffee56789a", "ref": "feature/awesome"},
            "base": {"ref": "main"},
            "user": {"login": "contributor1"},
        },
    }
    sync_bytes = json.dumps(sync_payload).encode("utf-8")
    sync_sig = sign_payload(sync_bytes, secret)

    sync_resp = client.post(
        "/api/v1/github/webhook",
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": sync_sig,
            "Content-Type": "application/json",
        },
        content=sync_bytes,
    )
    assert sync_resp.status_code == 200
    assert sync_resp.json()["verification_run_id"] == run_id

    # Verify updated record
    pr_verifs2 = client.get(f"/api/v1/github/pr-verifications?project_id={project_id}", headers=headers)
    assert pr_verifs2.status_code == 200
    assert len(pr_verifs2.json()) == 1
    assert pr_verifs2.json()[0]["pr_commit_sha"] == "c0ffee56789a"
    assert "Updated" in pr_verifs2.json()[0]["pr_title"]


def test_run_github_pr_verification_service():
    # Test that the background worker handles verification run lifecycle safely
    fake_run_id = uuid.uuid4()
    asyncio.run(run_github_pr_verification(fake_run_id))


def _configure_pr_project(client: TestClient, headers: dict[str, str], *, with_case: bool = False, active: bool = True):
    repo_name = f"org/pr-skip-{uuid.uuid4().hex[:8]}"
    secret = "pr-skip-secret"
    project_id = client.post(
        "/api/v1/projects", headers=headers, json={"name": "PR Skip Project"}
    ).json()["id"]
    client.patch(
        f"/api/v1/projects/{project_id}/github",
        headers=headers,
        json={
            "github_repo": repo_name,
            "github_verification_enabled": True,
            "github_webhook_secret": secret,
        },
    )
    suite_id = client.post(
        f"/api/v1/projects/{project_id}/test-suites",
        headers=headers,
        json={"name": "PR Suite"},
    ).json()["id"]
    if with_case:
        case = client.post(
            f"/api/v1/test-suites/{suite_id}/test-cases",
            headers=headers,
            json={
                "title": "Automated PR check",
                "steps": "Open the application",
                "expected_result": "The application opens",
                "execution_mode": "automated",
                "automation_steps": [{"action": "goto", "value": "https://example.com"}],
            },
        )
        assert case.status_code == 201
        if not active:
            disabled = client.patch(
                f"/api/v1/test-cases/{case.json()['id']}",
                headers=headers,
                json={"is_active": False},
            )
            assert disabled.status_code == 200
    payload = {
        "action": "opened",
        "repository": {"full_name": repo_name},
        "pull_request": {
            "number": 123,
            "title": "Skip unsuitable suite",
            "html_url": f"https://github.com/{repo_name}/pull/123",
            "head": {"sha": "feedface1234", "ref": "feature/skip"},
            "base": {"ref": "main"},
            "user": {"login": "contributor"},
        },
    }
    payload_bytes = json.dumps(payload).encode("utf-8")
    return project_id, payload_bytes, secret


@pytest.mark.parametrize("with_case,active", [(False, True), (True, False)])
def test_pr_webhook_skips_projects_without_active_automated_cases(
    client: TestClient, db_session, with_case: bool, active: bool
):
    headers = authenticated_headers(client, f"gh_skip_{uuid.uuid4().hex[:8]}@example.com")
    project_id, payload_bytes, secret = _configure_pr_project(
        client, headers, with_case=with_case, active=active
    )

    with patch("app.api.routes.github.post_github_commit_status", new=AsyncMock(return_value=True)) as post_status:
        response = client.post(
            "/api/v1/github/webhook",
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "skipped-delivery-123",
                "X-Hub-Signature-256": sign_payload(payload_bytes, secret),
                "Content-Type": "application/json",
            },
            content=payload_bytes,
        )
        replay = client.post(
            "/api/v1/github/webhook",
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "skipped-delivery-123",
                "X-Hub-Signature-256": sign_payload(payload_bytes, secret),
                "Content-Type": "application/json",
            },
            content=payload_bytes,
        )

    assert response.status_code == 200
    assert response.json()["status"] == "skipped"
    assert replay.status_code == 200
    assert db_session.scalars(select(VerificationRun)).all() == []
    assert not db_session.scalars(
        select(TestCase).where(TestCase.title.like("Verify Example Domain%"))
    ).all()
    post_status.assert_awaited_once()
    assert post_status.await_args.kwargs["state"] == "error"
    assert post_status.await_args.kwargs["description"] == (
        "VeriGate: no active automated test suite configured for this project"
    )
    audit = db_session.scalar(
        select(AuditLog).where(
            AuditLog.project_id == uuid.UUID(project_id),
            AuditLog.action == "skipped_github_pr",
        )
    )
    assert audit is not None
    assert audit.action == "skipped_github_pr"


def test_pr_webhook_active_case_creates_run_and_replay_is_idempotent(
    client: TestClient, db_session
):
    headers = authenticated_headers(client, f"gh_active_{uuid.uuid4().hex[:8]}@example.com")
    _, payload_bytes, secret = _configure_pr_project(client, headers, with_case=True)

    with patch("app.api.routes.github.run_github_pr_verification", new=AsyncMock()) as execute:
        first = client.post(
            "/api/v1/github/webhook",
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "delivery-123",
                "X-Hub-Signature-256": sign_payload(payload_bytes, secret),
                "Content-Type": "application/json",
            },
            content=payload_bytes,
        )
        replay = client.post(
            "/api/v1/github/webhook",
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "delivery-123",
                "X-Hub-Signature-256": sign_payload(payload_bytes, secret),
                "Content-Type": "application/json",
            },
            content=payload_bytes,
        )

    assert first.status_code == 200 and first.json()["status"] == "queued"
    assert replay.status_code == 200 and replay.json()["status"] == "duplicate"
    assert len(db_session.scalars(select(VerificationRun)).all()) == 1
    assert execute.await_count == 1

    async def mark_result_passed(_session, *, verification_run, **_kwargs):
        verification_run.results[0].status = "passed"

    with patch(
        "app.services.github_pr_verifier.execute_automated_results",
        new=AsyncMock(side_effect=mark_result_passed),
    ) as execute_results, patch(
        "app.services.github_pr_verifier.post_github_commit_status",
        new=AsyncMock(return_value=True),
    ) as post_status:
        asyncio.run(
            run_github_pr_verification(uuid.UUID(first.json()["run_id"]), db_session)
        )

    assert execute_results.await_count == 1
    assert [call.kwargs["state"] for call in post_status.await_args_list] == [
        "pending",
        "success",
    ]


def test_zero_result_run_is_not_completed_by_status_sync():
    run = VerificationRun(
        test_suite_id=uuid.uuid4(),
        created_by_id=uuid.uuid4(),
        name="Empty run",
        status="pending",
    )
    sync_verification_run_status(run)
    assert run.status == "pending"
