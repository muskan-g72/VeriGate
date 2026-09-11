import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient


def authenticated_headers(client: TestClient, email: str) -> dict[str, str]:
    password = "StrongPassword123!"
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Detective User"},
    )
    assert reg.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def setup_test_run(
    client: TestClient,
    headers: dict[str, str],
    *,
    result_status: str = "failed",
    failure_message: str | None = "Expected title 'Wrong Title', but got 'Example Domain'",
    stack_trace: str | None = "AssertionError: Expected title 'Wrong Title', but got 'Example Domain'",
    actual_result: str | None = "Page title is 'Example Domain'",
) -> tuple[str, str]:
    # 1. Create Project
    proj_resp = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "Detective Project", "description": "Testing AI Detective"},
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # 2. Create Test Suite
    suite_resp = client.post(
        f"/api/v1/projects/{project_id}/test-suites",
        headers=headers,
        json={"name": "Detective Suite"},
    )
    assert suite_resp.status_code == 201
    suite_id = suite_resp.json()["id"]

    # 3. Create Test Case
    case_resp = client.post(
        f"/api/v1/test-suites/{suite_id}/test-cases",
        headers=headers,
        json={
            "title": "Verify Example Domain - Failure Demo",
            "steps": "Navigate to example.com and verify title",
            "expected_result": "The page title should be 'Wrong Title'",
            "priority": "high",
            "execution_mode": "manual",
        },
    )
    assert case_resp.status_code == 201
    case_id = case_resp.json()["id"]

    # 4. Create Run
    run_resp = client.post(
        f"/api/v1/test-suites/{suite_id}/verification-runs",
        headers=headers,
        json={"name": "Detective Run"},
    )
    assert run_resp.status_code == 201
    run_id = run_resp.json()["id"]
    result_id = run_resp.json()["results"][0]["id"]

    # 5. Update Result
    patch_resp = client.patch(
        f"/api/v1/verification-results/{result_id}",
        headers=headers,
        json={
            "status": result_status,
            "failure_message": failure_message,
            "stack_trace": stack_trace,
            "actual_result": actual_result,
        },
    )
    assert patch_resp.status_code == 200

    return run_id, result_id


def test_analyze_verification_run_with_assertion_failure(client: TestClient) -> None:
    headers = authenticated_headers(client, "assertion.detective@example.com")
    run_id, result_id = setup_test_run(client, headers)

    response = client.post(
        f"/api/v1/verification-runs/{run_id}/analyze",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["has_failures"] is True
    assert len(data["analyses"]) == 1
    analysis = data["analyses"][0]
    assert analysis["failure_category"] == "Assertion Failure"
    assert "Wrong Title" in analysis["root_cause"]
    assert "Example Domain" in analysis["root_cause"]
    assert analysis["confidence"] >= 0.90
    assert "suggested_fix" in analysis
    assert "Failure message" in analysis["evidence_used"]
    assert "Stack trace" in analysis["evidence_used"]
    assert analysis["analysis_source"] == "heuristic_engine"


def test_analyze_verification_run_with_auth_failure(client: TestClient) -> None:
    headers = authenticated_headers(client, "auth.detective@example.com")
    run_id, result_id = setup_test_run(
        client,
        headers,
        failure_message="HTTP 401 Unauthorized: Could not validate credentials",
        stack_trace="HTTPError: 401 Unauthorized",
        actual_result="Received status 401",
    )

    response = client.post(
        f"/api/v1/verification-runs/{run_id}/analyze",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["has_failures"] is True
    analysis = data["analyses"][0]
    assert analysis["failure_category"] == "Authentication Failure"
    assert "Authentication" in analysis["root_cause"] or "credentials" in analysis["root_cause"].lower()
    assert analysis["confidence"] >= 0.85


def test_analyze_verification_run_with_element_not_found(client: TestClient) -> None:
    headers = authenticated_headers(client, "selector.detective@example.com")
    run_id, result_id = setup_test_run(
        client,
        headers,
        failure_message="TimeoutError: locator.wait_for: Timeout 30000ms exceeded waiting for locator('#submit-btn')",
        stack_trace="playwright._impl._errors.TimeoutError: locator.wait_for: Timeout 30000ms exceeded",
        actual_result="Element not found",
    )

    response = client.post(
        f"/api/v1/verification-runs/{run_id}/analyze",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["has_failures"] is True
    analysis = data["analyses"][0]
    assert analysis["failure_category"] == "Element Not Found"
    assert "element" in analysis["root_cause"].lower() or "timeout" in analysis["root_cause"].lower()


def test_analyze_verification_run_passed_run(client: TestClient) -> None:
    headers = authenticated_headers(client, "passed.detective@example.com")
    run_id, result_id = setup_test_run(
        client,
        headers,
        result_status="passed",
        failure_message=None,
        stack_trace=None,
        actual_result="All assertions passed",
    )

    response = client.post(
        f"/api/v1/verification-runs/{run_id}/analyze",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["has_failures"] is False
    assert len(data["analyses"]) == 0
    assert "No failed test cases" in data["summary"]


def test_analyze_verification_run_not_found(client: TestClient) -> None:
    headers = authenticated_headers(client, "missing.detective@example.com")
    random_id = uuid.uuid4()

    response = client.post(
        f"/api/v1/verification-runs/{random_id}/analyze",
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Verification run not found"


def test_analyze_verification_run_unauthorized_user(client: TestClient) -> None:
    headers_owner = authenticated_headers(client, "owner.detective@example.com")
    headers_other = authenticated_headers(client, "other.detective@example.com")
    run_id, _ = setup_test_run(client, headers_owner)

    response = client.post(
        f"/api/v1/verification-runs/{run_id}/analyze",
        headers=headers_other,
    )

    assert response.status_code in {403, 404}


def test_analyze_verification_result_endpoint(client: TestClient) -> None:
    headers = authenticated_headers(client, "single.detective@example.com")
    run_id, result_id = setup_test_run(client, headers)

    response = client.post(
        f"/api/v1/verification-results/{result_id}/analyze",
        headers=headers,
    )

    assert response.status_code == 200
    analysis = response.json()
    assert analysis["result_id"] == result_id
    assert analysis["failure_category"] == "Assertion Failure"
    assert analysis["confidence"] >= 0.90


def test_analyze_verification_run_llm_fallback_on_error(client: TestClient) -> None:
    headers = authenticated_headers(client, "fallback.detective@example.com")
    run_id, result_id = setup_test_run(client, headers)

    with patch("app.services.failure_analysis_service.settings.gemini_api_key", "mock-key"), \
         patch("app.services.failure_analysis_service.httpx.AsyncClient.post", side_effect=Exception("API Timeout")):
        response = client.post(
            f"/api/v1/verification-runs/{run_id}/analyze",
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["has_failures"] is True
    assert data["analyses"][0]["analysis_source"] == "heuristic_engine"
