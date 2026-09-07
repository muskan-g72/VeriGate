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
    assert issue["test_case_id"] is not None
    assert issue["verification_run_id"] is not None
    assert issue["severity"] == "critical"
    assert issue["priority"] == "medium"
    assert issue["status"] == "open"

    suites = client.get(f"/api/v1/projects/{project_id}/test-suites", headers=headers).json()
    runs = client.get(f"/api/v1/test-suites/{suites[0]['id']}/verification-runs", headers=headers).json()
    result = client.get(f"/api/v1/verification-runs/{runs[0]['id']}", headers=headers).json()['results'][0]
    assert result['status'] == 'failed'
    assert result['actual_result'] == 'Unexpected failure.'


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


def test_create_issue_from_blocked_result_preserves_verification(client: TestClient) -> None:
    headers, project_id, result_id = prepare_result(client)
    result = client.patch(f'/api/v1/verification-results/{result_id}', headers=headers,
                          json={'status': 'blocked', 'notes': 'Service unavailable'}).json()
    issue = create_issue(client, headers, result_id)
    assert issue['project_id'] == project_id
    run = client.get(f"/api/v1/verification-runs/{result['verification_run_id']}", headers=headers).json()
    assert run['results'][0]['status'] == 'blocked'
    assert run['results'][0]['notes'] == 'Service unavailable'


def test_passed_and_skipped_results_reject_issues(client: TestClient) -> None:
    headers, _, result_id = prepare_result(client)
    for status in ['passed', 'skipped']:
        assert client.patch(f'/api/v1/verification-results/{result_id}', headers=headers,
                            json={'status': status}).status_code == 200
        response = client.post(f'/api/v1/verification-results/{result_id}/issues', headers=headers,
                               json={'title': 'Invalid issue'})
        assert response.status_code == 400
        assert response.json()['detail'] == 'Issues can only be created from failed or blocked results'


def test_issue_edits_and_resolution_persist_on_read_and_list(client: TestClient) -> None:
    headers, project_id, result_id = prepare_result(client)
    fail_result(client, headers, result_id)
    issue = create_issue(client, headers, result_id)
    url = f"/api/v1/issues/{issue['id']}"
    for status in ['in_progress', 'resolved', 'closed', 'open', 'closed', 'in_progress']:
        saved = client.patch(url, headers=headers, json={
            'title': 'Updated finding', 'description': 'Investigated login failure',
            'severity': 'high', 'status': status,
        })
        assert saved.status_code == 200
        data = saved.json()
        assert (data['resolved_at'] is not None) == (status in ['resolved', 'closed'])
        assert client.get(url, headers=headers).json() == data
        listed = client.get(f'/api/v1/projects/{project_id}/issues', headers=headers).json()
        assert listed == [data]
        assert data['severity'] == 'high'
        assert data['title'] == 'Updated finding'


def test_issue_project_list_and_update_are_owner_protected(client: TestClient) -> None:
    headers, project_id, result_id = prepare_result(client)
    fail_result(client, headers, result_id)
    issue = create_issue(client, headers, result_id)
    other, _, _ = prepare_result(client, 'other.issue@example.com')
    assert client.get(f'/api/v1/projects/{project_id}/issues', headers=other).status_code == 404
    assert client.patch(f"/api/v1/issues/{issue['id']}", headers=other,
                        json={'status': 'closed'}).status_code == 404
