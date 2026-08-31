from fastapi.testclient import TestClient


def build_test_suite(client: TestClient, email: str) -> tuple[dict[str, str], str]:
    password = "StrongPassword123!"
    register = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Case Owner"},
    )
    assert register.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    project = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "VeriGate"},
    )
    assert project.status_code == 201
    test_suite = client.post(
        f"/api/v1/projects/{project.json()['id']}/test-suites",
        headers=headers,
        json={"name": "Authentication"},
    )
    assert test_suite.status_code == 201
    return headers, test_suite.json()["id"]


def create_test_case(
    client: TestClient,
    headers: dict[str, str],
    test_suite_id: str,
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/test-suites/{test_suite_id}/test-cases",
        headers=headers,
        json={
            "title": "Valid user can log in",
            "description": "Verify email and password login.",
            "steps": "1. Enter credentials\n2. Submit the login form",
            "expected_result": "A bearer access token is returned.",
            "priority": "high",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_create_test_case(client: TestClient) -> None:
    headers, suite_id = build_test_suite(client, "case.owner@example.com")
    test_case = create_test_case(client, headers, suite_id)

    assert test_case["test_suite_id"] == suite_id
    assert test_case["priority"] == "high"
    assert test_case["is_active"] is True


def test_list_test_cases(client: TestClient) -> None:
    headers, suite_id = build_test_suite(client, "case.owner@example.com")
    test_case = create_test_case(client, headers, suite_id)

    response = client.get(
        f"/api/v1/test-suites/{suite_id}/test-cases",
        headers=headers,
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [test_case["id"]]


def test_read_test_case(client: TestClient) -> None:
    headers, suite_id = build_test_suite(client, "case.owner@example.com")
    test_case = create_test_case(client, headers, suite_id)

    response = client.get(
        f"/api/v1/test-cases/{test_case['id']}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == test_case["id"]


def test_update_and_deactivate_test_case(client: TestClient) -> None:
    headers, suite_id = build_test_suite(client, "case.owner@example.com")
    test_case = create_test_case(client, headers, suite_id)

    response = client.patch(
        f"/api/v1/test-cases/{test_case['id']}",
        headers=headers,
        json={"priority": "critical", "is_active": False},
    )

    assert response.status_code == 200
    assert response.json()["priority"] == "critical"
    assert response.json()["is_active"] is False


def test_rejects_invalid_priority(client: TestClient) -> None:
    headers, suite_id = build_test_suite(client, "case.owner@example.com")
    response = client.post(
        f"/api/v1/test-suites/{suite_id}/test-cases",
        headers=headers,
        json={
            "title": "Invalid priority",
            "steps": "Perform an action",
            "expected_result": "Action succeeds",
            "priority": "urgent",
        },
    )

    assert response.status_code == 422


def test_cannot_create_case_in_another_users_suite(client: TestClient) -> None:
    _, suite_id = build_test_suite(client, "case.owner@example.com")
    other_headers, _ = build_test_suite(client, "other.case.owner@example.com")

    response = client.post(
        f"/api/v1/test-suites/{suite_id}/test-cases",
        headers=other_headers,
        json={
            "title": "Unauthorized case",
            "steps": "Attempt creation",
            "expected_result": "Request is rejected",
        },
    )

    assert response.status_code == 404


def test_cannot_read_another_users_test_case(client: TestClient) -> None:
    owner_headers, suite_id = build_test_suite(client, "case.owner@example.com")
    test_case = create_test_case(client, owner_headers, suite_id)
    other_headers, _ = build_test_suite(client, "other.case.owner@example.com")

    response = client.get(
        f"/api/v1/test-cases/{test_case['id']}",
        headers=other_headers,
    )

    assert response.status_code == 404


def test_required_text_fields_cannot_be_blank(client: TestClient) -> None:
    headers, suite_id = build_test_suite(client, "case.owner@example.com")
    response = client.post(
        f"/api/v1/test-suites/{suite_id}/test-cases",
        headers=headers,
        json={
            "title": "   ",
            "steps": "   ",
            "expected_result": "   ",
        },
    )

    assert response.status_code == 422


def test_delete_owned_test_case(client: TestClient) -> None:
    headers, suite_id = build_test_suite(client, "delete.case@example.com")
    test_case = create_test_case(client, headers, suite_id)

    response = client.delete(
        f"/api/v1/test-cases/{test_case['id']}", headers=headers
    )

    assert response.status_code == 204
    assert client.get(
        f"/api/v1/test-cases/{test_case['id']}", headers=headers
    ).status_code == 404


def test_cannot_delete_another_users_test_case(client: TestClient) -> None:
    owner_headers, suite_id = build_test_suite(
        client, "delete.case.owner@example.com"
    )
    test_case = create_test_case(client, owner_headers, suite_id)
    other_headers, _ = build_test_suite(client, "delete.case.other@example.com")

    response = client.delete(
        f"/api/v1/test-cases/{test_case['id']}", headers=other_headers
    )

    assert response.status_code == 404
