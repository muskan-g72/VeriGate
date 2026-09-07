from fastapi.testclient import TestClient


def authenticated_headers(client: TestClient, email: str) -> dict[str, str]:
    password = "StrongPassword123!"
    assert client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Run Owner"},
    ).status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def create_suite(client: TestClient, headers: dict[str, str]) -> str:
    project = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "Verification Project"},
    )
    assert project.status_code == 201
    suite = client.post(
        f"/api/v1/projects/{project.json()['id']}/test-suites",
        headers=headers,
        json={"name": "Regression Suite"},
    )
    assert suite.status_code == 201
    return suite.json()["id"]


def create_case(
    client: TestClient,
    headers: dict[str, str],
    suite_id: str,
    title: str,
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/test-suites/{suite_id}/test-cases",
        headers=headers,
        json={
            "title": title,
            "steps": "Perform the test steps.",
            "expected_result": "The expected behavior occurs.",
        },
    )
    assert response.status_code == 201
    return response.json()


def create_run_context(
    client: TestClient,
    email: str = "run.owner@example.com",
) -> tuple[dict[str, str], str]:
    headers = authenticated_headers(client, email)
    suite_id = create_suite(client, headers)
    create_case(client, headers, suite_id, "First case")
    create_case(client, headers, suite_id, "Second case")
    return headers, suite_id


def start_run(
    client: TestClient,
    headers: dict[str, str],
    suite_id: str,
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/test-suites/{suite_id}/verification-runs",
        headers=headers,
        json={"name": "Release verification"},
    )
    assert response.status_code == 201
    return response.json()


def test_create_run_snapshots_active_test_cases(client: TestClient) -> None:
    headers, suite_id = create_run_context(client)
    inactive_case = create_case(client, headers, suite_id, "Inactive case")
    assert client.patch(
        f"/api/v1/test-cases/{inactive_case['id']}",
        headers=headers,
        json={"is_active": False},
    ).status_code == 200

    run = start_run(client, headers, suite_id)

    assert run["status"] == "pending"
    assert len(run["results"]) == 2
    assert run["total_cases"] == 2
    assert run["pending_count"] == 2
    assert run["passed_count"] == 0
    assert {result["status"] for result in run["results"]} == {"pending"}


def test_cannot_create_run_without_active_cases(client: TestClient) -> None:
    headers = authenticated_headers(client, "empty.run@example.com")
    suite_id = create_suite(client, headers)

    response = client.post(
        f"/api/v1/test-suites/{suite_id}/verification-runs",
        headers=headers,
        json={"name": "Empty run"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Test suite has no active test cases"


def test_list_and_read_runs(client: TestClient) -> None:
    headers, suite_id = create_run_context(client)
    run = start_run(client, headers, suite_id)

    listed = client.get(
        f"/api/v1/test-suites/{suite_id}/verification-runs",
        headers=headers,
    )
    detail = client.get(
        f"/api/v1/verification-runs/{run['id']}",
        headers=headers,
    )

    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [run["id"]]
    assert detail.status_code == 200
    assert len(detail.json()["results"]) == 2


def test_updating_results_advances_and_completes_run(client: TestClient) -> None:
    headers, suite_id = create_run_context(client)
    run = start_run(client, headers, suite_id)
    first_result, second_result = run["results"]

    first_update = client.patch(
        f"/api/v1/verification-results/{first_result['id']}",
        headers=headers,
        json={
            "status": "passed",
            "actual_result": "The expected behavior occurred.",
        },
    )
    assert first_update.status_code == 200
    assert first_update.json()["executed_at"] is not None

    in_progress = client.get(
        f"/api/v1/verification-runs/{run['id']}",
        headers=headers,
    ).json()
    assert in_progress["status"] == "in_progress"
    assert in_progress["passed_count"] == 1
    assert in_progress["pending_count"] == 1
    assert in_progress["started_at"] is not None
    assert in_progress["completed_at"] is None

    second_update = client.patch(
        f"/api/v1/verification-results/{second_result['id']}",
        headers=headers,
        json={"status": "failed", "notes": "Unexpected response."},
    )
    assert second_update.status_code == 200

    completed = client.get(
        f"/api/v1/verification-runs/{run['id']}",
        headers=headers,
    ).json()
    assert completed["status"] == "completed"
    assert completed["passed_count"] == 1
    assert completed["failed_count"] == 1
    assert completed["pending_count"] == 0
    assert completed["completed_at"] is not None


def test_update_result_stores_failure_investigation_fields(
    client: TestClient,
) -> None:
    headers, suite_id = create_run_context(client)
    run = start_run(client, headers, suite_id)
    result_id = run["results"][0]["id"]

    response = client.patch(
        f"/api/v1/verification-results/{result_id}",
        headers=headers,
        json={
            "status": "failed",
            "actual_result": "Got HTTP 500",
            "failure_message": "Internal Server Error",
            "stack_trace": "Traceback (most recent call last)...",
            "duration": 1.25,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "failed"
    assert payload["actual_result"] == "Got HTTP 500"
    assert payload["failure_message"] == "Internal Server Error"
    assert payload["stack_trace"] == "Traceback (most recent call last)..."
    assert payload["duration"] == 1.25
    assert payload["executed_at"] is not None


def test_running_status_does_not_complete_run(client: TestClient) -> None:
    headers, suite_id = create_run_context(client)
    run = start_run(client, headers, suite_id)
    first_result, second_result = run["results"]

    client.patch(
        f"/api/v1/verification-results/{first_result['id']}",
        headers=headers,
        json={"status": "running"},
    )
    in_progress = client.get(
        f"/api/v1/verification-runs/{run['id']}",
        headers=headers,
    ).json()
    assert in_progress["status"] == "in_progress"
    assert in_progress["completed_at"] is None

    client.patch(
        f"/api/v1/verification-results/{first_result['id']}",
        headers=headers,
        json={"status": "passed"},
    )
    still_in_progress = client.get(
        f"/api/v1/verification-runs/{run['id']}",
        headers=headers,
    ).json()
    assert still_in_progress["status"] == "in_progress"

    client.patch(
        f"/api/v1/verification-results/{second_result['id']}",
        headers=headers,
        json={"status": "passed"},
    )
    completed = client.get(
        f"/api/v1/verification-runs/{run['id']}",
        headers=headers,
    ).json()
    assert completed["status"] == "completed"


def test_invalid_result_status_is_rejected(client: TestClient) -> None:
    headers, suite_id = create_run_context(client)
    run = start_run(client, headers, suite_id)

    response = client.patch(
        f"/api/v1/verification-results/{run['results'][0]['id']}",
        headers=headers,
        json={"status": "successful"},
    )

    assert response.status_code == 422


def test_other_user_cannot_read_run_or_update_result(client: TestClient) -> None:
    owner_headers, suite_id = create_run_context(client)
    run = start_run(client, owner_headers, suite_id)
    other_headers = authenticated_headers(client, "other.run.owner@example.com")

    read_response = client.get(
        f"/api/v1/verification-runs/{run['id']}",
        headers=other_headers,
    )
    update_response = client.patch(
        f"/api/v1/verification-results/{run['results'][0]['id']}",
        headers=other_headers,
        json={"status": "passed"},
    )

    assert read_response.status_code == 404
    assert update_response.status_code == 404


def test_run_reopens_with_details_and_resets_from_completed(client: TestClient) -> None:
    headers, suite_id = create_run_context(client)
    run = start_run(client, headers, suite_id)
    first, second = run['results']
    for result, result_status in [(first, 'blocked'), (second, 'skipped')]:
        response = client.patch(
            f"/api/v1/verification-results/{result['id']}",
            headers=headers,
            json={'status': result_status, 'actual_result': 'Service unavailable', 'notes': 'Retry later'},
        )
        assert response.status_code == 200

    detail_url = f"/api/v1/verification-runs/{run['id']}"
    reopened = client.get(detail_url, headers=headers).json()
    assert reopened['status'] == 'completed'
    assert reopened['blocked_count'] == reopened['skipped_count'] == 1
    assert all(item['actual_result'] == 'Service unavailable' and item['notes'] == 'Retry later' for item in reopened['results'])
    history = client.get(f'/api/v1/test-suites/{suite_id}/verification-runs', headers=headers).json()
    assert history[0]['id'] == run['id']
    assert history[0]['status'] == 'completed'

    for index, result in enumerate([first, second]):
        saved = client.patch(
            f"/api/v1/verification-results/{result['id']}",
            headers=headers,
            json={'status': 'pending', 'actual_result': None, 'notes': None},
        ).json()
        assert saved['executed_at'] is None
        assert saved['actual_result'] is None
        assert saved['notes'] is None
        current = client.get(detail_url, headers=headers).json()
        assert current['status'] == ('in_progress' if index == 0 else 'pending')
        assert current['completed_at'] is None
    assert current['started_at'] is None
    assert current['pending_count'] == 2
