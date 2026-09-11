import uuid

from fastapi.testclient import TestClient


def authenticated_headers(client: TestClient, email: str) -> dict[str, str]:
    password = "StrongPassword123!"
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Report User"},
    )
    assert reg.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def setup_report_test_run(
    client: TestClient,
    headers: dict[str, str],
    *,
    has_failure: bool = True,
    secret_in_failure: bool = False,
) -> tuple[str, str, str]:
    # 1. Project
    p_resp = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "Report Project", "description": "Verification report testing"},
    )
    assert p_resp.status_code == 201
    project_id = p_resp.json()["id"]

    # 2. Test Suite
    s_resp = client.post(
        f"/api/v1/projects/{project_id}/test-suites",
        headers=headers,
        json={"name": "Report Suite"},
    )
    assert s_resp.status_code == 201
    suite_id = s_resp.json()["id"]

    # 3. Test Cases
    tc1_resp = client.post(
        f"/api/v1/test-suites/{suite_id}/test-cases",
        headers=headers,
        json={
            "title": "TC 1 - Authenticate Session",
            "steps": "Send valid credentials to login endpoint",
            "expected_result": "Status 200 with JWT token",
            "priority": "high",
            "execution_mode": "manual",
        },
    )
    assert tc1_resp.status_code == 201

    tc2_resp = client.post(
        f"/api/v1/test-suites/{suite_id}/test-cases",
        headers=headers,
        json={
            "title": "TC 2 - Verify User Dashboard",
            "steps": "Load dashboard and verify title",
            "expected_result": "Page title should be 'Command Center'",
            "priority": "critical",
            "execution_mode": "manual",
        },
    )
    assert tc2_resp.status_code == 201

    # 4. Verification Run
    run_resp = client.post(
        f"/api/v1/test-suites/{suite_id}/verification-runs",
        headers=headers,
        json={"name": "Release Verification 1.0"},
    )
    assert run_resp.status_code == 201
    run = run_resp.json()
    run_id = run["id"]
    results = run["results"]

    # 5. Result 1: passed
    client.patch(
        f"/api/v1/verification-results/{results[0]['id']}",
        headers=headers,
        json={"status": "passed", "notes": "Authentication passed smoothly."},
    )

    # 6. Result 2
    if has_failure:
        failure_msg = (
            "Expected 'Command Center', got 'Error 500' with password=SuperSecret123! and Bearer eyJhbGciOiJIUzI1NiJ9.test.sig"
            if secret_in_failure
            else "AssertionError: Expected 'Command Center', got 'Error 500'"
        )
        client.patch(
            f"/api/v1/verification-results/{results[1]['id']}",
            headers=headers,
            json={
                "status": "failed",
                "failure_message": failure_msg,
                "stack_trace": "AssertionError: Expected 'Command Center', got 'Error 500'\n  at test_dashboard.py:45",
                "actual_result": "Received 500 Internal Server Error",
            },
        )
        # Attach evidence
        client.post(
            f"/api/v1/verification-results/{results[1]['id']}/evidence",
            headers=headers,
            json={
                "name": "dashboard-failure-screenshot",
                "type": "screenshot",
                "description": "Captured failure on test step 2",
                # 1x1 transparent PNG base64
                "content": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            },
        )
    else:
        client.patch(
            f"/api/v1/verification-results/{results[1]['id']}",
            headers=headers,
            json={"status": "passed", "actual_result": "Page title is 'Command Center'"},
        )

    return project_id, suite_id, run_id


def test_generate_verification_report_json_format(client: TestClient):
    headers = authenticated_headers(client, "report_json_user@example.com")
    _, _, run_id = setup_report_test_run(client, headers, has_failure=True)

    resp = client.get(
        f"/api/v1/verification-runs/{run_id}/report?format=json",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert "report_id" in data
    assert "generated_at" in data
    assert data["verification_run"]["name"] == "Release Verification 1.0"
    assert data["verification_run"]["overall_status"] == "FAILED"
    assert data["summary"]["total_tests"] == 2
    assert data["summary"]["passed_tests"] == 1
    assert data["summary"]["failed_tests"] == 1
    assert data["summary"]["pass_rate"] == 50.0

    # Timeline verification
    assert len(data["timeline"]) >= 3
    events = [item["event"] for item in data["timeline"]]
    assert any("Initialized" in e for e in events)

    # Test cases breakdown
    assert len(data["test_cases"]) == 2
    failed_tc = next(c for c in data["test_cases"] if c["status"] == "failed")
    assert failed_tc["ai_diagnosis"] is not None
    assert "Assertion" in failed_tc["ai_diagnosis"]["category"]
    assert failed_tc["ai_diagnosis"]["confidence"] in ["High", "Medium", "Low"]

    # Evidence verification
    assert len(failed_tc["evidence"]) == 1
    assert failed_tc["evidence"][0]["name"] == "dashboard-failure-screenshot"
    assert failed_tc["evidence"][0]["type"] == "screenshot"


def test_generate_verification_report_pdf_format(client: TestClient):
    headers = authenticated_headers(client, "report_pdf_user@example.com")
    _, _, run_id = setup_report_test_run(client, headers, has_failure=True)

    resp = client.get(
        f"/api/v1/verification-runs/{run_id}/report?format=pdf",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "attachment; filename=" in resp.headers["content-disposition"]
    # PDF magic bytes
    assert resp.content.startswith(b"%PDF")
    assert len(resp.content) > 1000


def test_generate_report_for_passed_run(client: TestClient):
    headers = authenticated_headers(client, "report_passed_user@example.com")
    _, _, run_id = setup_report_test_run(client, headers, has_failure=False)

    resp = client.get(
        f"/api/v1/verification-runs/{run_id}/report?format=json",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["verification_run"]["overall_status"] == "PASSED"
    assert data["summary"]["failed_tests"] == 0
    assert data["summary"]["pass_rate"] == 100.0


def test_generate_report_sanitizes_secrets(client: TestClient):
    headers = authenticated_headers(client, "report_security_user@example.com")
    _, _, run_id = setup_report_test_run(
        client, headers, has_failure=True, secret_in_failure=True
    )

    resp = client.get(
        f"/api/v1/verification-runs/{run_id}/report?format=json",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    failed_tc = next(c for c in data["test_cases"] if c["status"] == "failed")
    failure_msg = failed_tc["failure_message"]

    # Ensure passwords and tokens were redacted
    assert "SuperSecret123!" not in failure_msg
    assert "[REDACTED]" in failure_msg
    assert "[REDACTED_TOKEN]" in failure_msg or "[REDACTED_JWT]" in failure_msg


def test_generate_report_unauthorized_and_missing_run(client: TestClient):
    # 1. Unauthenticated request
    unauth = client.get(f"/api/v1/verification-runs/{uuid.uuid4()}/report")
    assert unauth.status_code == 401

    # 2. Non-existent run ID
    headers1 = authenticated_headers(client, "report_owner1@example.com")
    missing = client.get(
        f"/api/v1/verification-runs/{uuid.uuid4()}/report",
        headers=headers1,
    )
    assert missing.status_code == 404

    # 3. Foreign run access isolation
    _, _, run_id = setup_report_test_run(client, headers1)
    headers2 = authenticated_headers(client, "report_intruder@example.com")
    forbidden = client.get(
        f"/api/v1/verification-runs/{run_id}/report",
        headers=headers2,
    )
    assert forbidden.status_code in [403, 404]


def test_generate_verification_report_aliases(client: TestClient):
    headers = authenticated_headers(client, "report_aliases@example.com")
    _, _, run_id = setup_report_test_run(client, headers, has_failure=False)

    # Test /api/v1/verification-runs/{run_id}/reports
    resp1 = client.get(
        f"/api/v1/verification-runs/{run_id}/reports?format=json",
        headers=headers,
    )
    assert resp1.status_code == 200

    # Test /api/v1/reports/verification/{run_id}
    resp2 = client.get(
        f"/api/v1/reports/verification/{run_id}?format=json",
        headers=headers,
    )
    assert resp2.status_code == 200

    # Test /api/v1/reports/{run_id}
    resp3 = client.get(
        f"/api/v1/reports/{run_id}?format=json",
        headers=headers,
    )
    assert resp3.status_code == 200


def test_generate_report_pdf_handles_playwright_failure_gracefully(client: TestClient, monkeypatch):
    headers = authenticated_headers(client, "report_failure_user@example.com")
    _, _, run_id = setup_report_test_run(client, headers, has_failure=False)

    import app.api.routes.reports as reports_module

    async def mock_fail_pdf(report_data):
        raise RuntimeError("Chromium executable not found")

    monkeypatch.setattr(reports_module, "generate_verification_report_pdf", mock_fail_pdf)

    resp = client.get(
        f"/api/v1/verification-runs/{run_id}/report?format=pdf",
        headers=headers,
    )
    assert resp.status_code == 500
    assert "Verification report PDF generation failed: Chromium executable not found" in resp.json()["detail"]
