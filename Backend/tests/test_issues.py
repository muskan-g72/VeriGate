from fastapi.testclient import TestClient


def prepare_result(
    client: TestClient,
    email: str = "issue.owner@example.com",
) -> tuple[dict[str, str], str, str]:
    password = "StrongPassword123!"
    user = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Issue Owner"},
    )
    assert user.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    project = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "Issue Project"},
    )
    project_id = project.json()["id"]
    suite = client.post(
        f"/api/v1/projects/{project_id}/test-suites",
        headers=headers,
        json={"name": "Issue Suite"},
    )
    case = client.post(
        f"/api/v1/test-suites/{suite.json()['id']}/test-cases",
        headers=headers,
        json={
            "title": "Failure case",
            "steps": "Execute the scenario.",
            "expected_result": "The scenario succeeds.",
        },
    )
    run = client.post(
        f"/api/v1/test-suites/{suite.json()['id']}/verification-runs",
        headers=headers,
        json={"name": "Issue run"},
    )
    assert case.status_code == 201
    assert run.status_code == 201
    return headers, project_id, run.json()["results"][0]["id"]


def fail_result(
    client: TestClient,
    headers: dict[str, str],
    result_id: str,
) -> None:
    response = client.patch(
        f"/api/v1/verification-results/{result_id}",
        headers=headers,
        json={"status": "failed", "actual_result": "Unexpected failure."},
    )
    assert response.status_code == 200


def create_issue(
    client: TestClient,
    headers: dict[str, str],
    result_id: str,
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/verification-results/{result_id}/issues",
        headers=headers,
        json={
            "title": "Login endpoint returned 500",
            "description": "The endpoint failed during verification.",
            "severity": "critical",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_create_issue_from_failed_result(client: TestClient) -> None:
    headers, project_id, result_id = prepare_result(client)
    fail_result(client, headers, result_id)
    issue = create_issue(client, headers, result_id)

    assert issue["project_id"] == project_id
    assert issue["verification_result_id"] == result_id
    assert issue["severity"] == "critical"
    assert issue["status"] == "open"


def test_cannot_create_issue_from_pending_result(client: TestClient) -> None:
    headers, _, result_id = prepare_result(client)

    response = client.post(
        f"/api/v1/verification-results/{result_id}/issues",
        headers=headers,
        json={"title": "Premature issue"},
    )

    assert response.status_code == 400


def test_list_and_read_issues(client: TestClient) -> None:
    headers, project_id, result_id = prepare_result(client)
    fail_result(client, headers, result_id)
    issue = create_issue(client, headers, result_id)

    listed = client.get(f"/api/v1/projects/{project_id}/issues", headers=headers)
    detail = client.get(f"/api/v1/issues/{issue['id']}", headers=headers)

    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [issue["id"]]
    assert detail.status_code == 200


def test_resolve_and_reopen_issue(client: TestClient) -> None:
    headers, _, result_id = prepare_result(client)
    fail_result(client, headers, result_id)
    issue = create_issue(client, headers, result_id)

    resolved = client.patch(
        f"/api/v1/issues/{issue['id']}",
        headers=headers,
        json={"status": "resolved"},
    )
    assert resolved.status_code == 200
    assert resolved.json()["resolved_at"] is not None

    reopened = client.patch(
        f"/api/v1/issues/{issue['id']}",
        headers=headers,
        json={"status": "open"},
    )
    assert reopened.status_code == 200
    assert reopened.json()["resolved_at"] is None


def test_other_user_cannot_access_issue(client: TestClient) -> None:
    headers, _, result_id = prepare_result(client)
    fail_result(client, headers, result_id)
    issue = create_issue(client, headers, result_id)
    other_headers, _, _ = prepare_result(client, "other.issue.owner@example.com")

    response = client.get(f"/api/v1/issues/{issue['id']}", headers=other_headers)

    assert response.status_code == 404
