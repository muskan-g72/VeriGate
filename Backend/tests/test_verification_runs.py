from unittest.mock import AsyncMock, patch

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


AUTOMATION_STEPS = [
    {"action": "goto", "value": "https://example.com"},
    {"action": "expect_title", "value": "Example Domain"},
]


def create_automated_case(
    client: TestClient,
    headers: dict[str, str],
    suite_id: str,
    title: str = "Automated homepage check",
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/test-suites/{suite_id}/test-cases",
        headers=headers,
        json={
            "title": title,
            "steps": "Open example.com and check the title.",
            "expected_result": "The title is Example Domain.",
            "execution_mode": "automated",
            "automation_steps": AUTOMATION_STEPS,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_create_manual_verification_run(client: TestClient) -> None:
    headers, suite_id = create_run_context(client, "manual.run@example.com")
    run = start_run(client, headers, suite_id)

    assert run["status"] == "pending"
    assert {result["status"] for result in run["results"]} == {"pending"}
    assert all(result["evidence_items"] == [] for result in run["results"])
    assert all(result["actual_result"] is None for result in run["results"])


def test_create_automated_verification_run_invokes_playwright(
    client: TestClient,
) -> None:
    headers = authenticated_headers(client, "auto.run@example.com")
    suite_id = create_suite(client, headers)
    create_automated_case(client, headers, suite_id)
    playwright_result = {
        "status": "passed",
        "actual_result": "Test passed",
        "failure_message": None,
        "stack_trace": None,
        "duration": 0.42,
        "screenshot": None,
    }

    with patch(
        "app.services.automated_verification.execute_playwright_test",
        new_callable=AsyncMock,
        return_value=playwright_result,
    ) as execute_playwright_test:
        run = start_run(client, headers, suite_id)

    execute_playwright_test.assert_awaited_once_with(AUTOMATION_STEPS)
    assert run["status"] == "completed"
    assert run["passed_count"] == 1
    result = run["results"][0]
    assert result["status"] == "passed"
    assert result["actual_result"] == "Test passed"
    assert result["failure_message"] is None
    assert result["stack_trace"] is None
    assert result["duration"] == 0.42
    assert result["executed_at"] is not None
    assert result["evidence_items"] == []


def test_automated_run_saves_screenshot_as_evidence(client: TestClient) -> None:
    headers = authenticated_headers(client, "auto.screenshot@example.com")
    suite_id = create_suite(client, headers)
    create_automated_case(client, headers, suite_id)
    screenshot = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    playwright_result = {
        "status": "failed",
        "actual_result": "Test failed",
        "failure_message": "Expected title 'Example Domain', but got 'Other'",
        "stack_trace": "Traceback (most recent call last): ...",
        "duration": 1.5,
        "screenshot": screenshot,
    }

    with patch(
        "app.services.automated_verification.execute_playwright_test",
        new_callable=AsyncMock,
        return_value=playwright_result,
    ):
        run = start_run(client, headers, suite_id)

    assert run["status"] == "completed"
    assert run["failed_count"] == 1
    result = run["results"][0]
    assert result["status"] == "failed"
    assert result["actual_result"] == "Test failed"
    assert result["failure_message"] == playwright_result["failure_message"]
    assert result["stack_trace"] == playwright_result["stack_trace"]
    assert result["duration"] == 1.5
    assert len(result["evidence_items"]) == 1
    evidence = result["evidence_items"][0]
    assert evidence["type"] == "screenshot"
    assert evidence["name"] == "Playwright screenshot"
    assert evidence["content"] == screenshot
    assert evidence["verification_result_id"] == result["id"]

    listed = client.get(
        f"/api/v1/verification-results/{result['id']}/evidence",
        headers=headers,
    )
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == evidence["id"]


def test_playwright_executor_not_invoked_for_manual_runs(
    client: TestClient,
) -> None:
    headers, suite_id = create_run_context(client, "manual.no.playwright@example.com")

    with patch(
        "app.services.automated_verification.execute_playwright_test",
        new_callable=AsyncMock,
    ) as execute_playwright_test:
        start_run(client, headers, suite_id)

    execute_playwright_test.assert_not_called()


def test_mixed_suite_executes_only_automated_cases(client: TestClient) -> None:
    headers = authenticated_headers(client, "mixed.run@example.com")
    suite_id = create_suite(client, headers)
    create_case(client, headers, suite_id, "Manual case")
    create_automated_case(client, headers, suite_id)
    playwright_result = {
        "status": "passed",
        "actual_result": "Test passed",
        "failure_message": None,
        "stack_trace": None,
        "duration": 0.2,
        "screenshot": None,
    }

    with patch(
        "app.services.automated_verification.execute_playwright_test",
        new_callable=AsyncMock,
        return_value=playwright_result,
    ) as execute_playwright_test:
        run = start_run(client, headers, suite_id)

    execute_playwright_test.assert_awaited_once()
    statuses = {result["test_case_id"]: result["status"] for result in run["results"]}
    assert "pending" in statuses.values()
    assert "passed" in statuses.values()
    assert run["status"] == "in_progress"


def test_playwright_exception_is_stored_as_failure(client: TestClient) -> None:
    headers = authenticated_headers(client, "auto.exception@example.com")
    suite_id = create_suite(client, headers)
    create_automated_case(client, headers, suite_id)

    with patch(
        "app.services.automated_verification.execute_playwright_test",
        new_callable=AsyncMock,
        side_effect=RuntimeError("browser launch failed"),
    ):
        run = start_run(client, headers, suite_id)

    result = run["results"][0]
    assert run["status"] == "completed"
    assert result["status"] == "failed"
    assert result["actual_result"] == "Test failed"
    assert result["failure_message"] == "browser launch failed"
    assert result["evidence_items"] == []

