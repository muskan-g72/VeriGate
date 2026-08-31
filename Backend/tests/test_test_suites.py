from fastapi.testclient import TestClient


def create_user_headers(client: TestClient, email: str) -> dict[str, str]:
    password = "StrongPassword123!"
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Suite Owner"},
    )
    assert register_response.status_code == 201
    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert login_response.status_code == 200
    return {
        "Authorization": f"Bearer {login_response.json()['access_token']}"
    }


def create_project(client: TestClient, headers: dict[str, str]) -> dict[str, object]:
    response = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "VeriGate", "description": "Verification project"},
    )
    assert response.status_code == 201
    return response.json()


def create_test_suite(
    client: TestClient,
    headers: dict[str, str],
    project_id: object,
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/projects/{project_id}/test-suites",
        headers=headers,
        json={"name": "Authentication", "description": "Authentication tests"},
    )
    assert response.status_code == 201
    return response.json()


def test_create_test_suite(client: TestClient) -> None:
    headers = create_user_headers(client, "suite.owner@example.com")
    project = create_project(client, headers)
    test_suite = create_test_suite(client, headers, project["id"])

    assert test_suite["project_id"] == project["id"]
    assert test_suite["name"] == "Authentication"


def test_list_project_test_suites(client: TestClient) -> None:
    headers = create_user_headers(client, "suite.owner@example.com")
    project = create_project(client, headers)
    test_suite = create_test_suite(client, headers, project["id"])

    response = client.get(
        f"/api/v1/projects/{project['id']}/test-suites",
        headers=headers,
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [test_suite["id"]]


def test_read_test_suite(client: TestClient) -> None:
    headers = create_user_headers(client, "suite.owner@example.com")
    project = create_project(client, headers)
    test_suite = create_test_suite(client, headers, project["id"])

    response = client.get(
        f"/api/v1/test-suites/{test_suite['id']}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == test_suite["id"]


def test_update_test_suite(client: TestClient) -> None:
    headers = create_user_headers(client, "suite.owner@example.com")
    project = create_project(client, headers)
    test_suite = create_test_suite(client, headers, project["id"])

    response = client.patch(
        f"/api/v1/test-suites/{test_suite['id']}",
        headers=headers,
        json={"name": "Updated authentication suite"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated authentication suite"


def test_cannot_create_suite_in_another_users_project(
    client: TestClient,
) -> None:
    owner_headers = create_user_headers(client, "suite.owner@example.com")
    project = create_project(client, owner_headers)
    other_headers = create_user_headers(client, "other.suite.owner@example.com")

    response = client.post(
        f"/api/v1/projects/{project['id']}/test-suites",
        headers=other_headers,
        json={"name": "Unauthorized suite"},
    )

    assert response.status_code == 404


def test_cannot_read_another_users_test_suite(client: TestClient) -> None:
    owner_headers = create_user_headers(client, "suite.owner@example.com")
    project = create_project(client, owner_headers)
    test_suite = create_test_suite(client, owner_headers, project["id"])
    other_headers = create_user_headers(client, "other.suite.owner@example.com")

    response = client.get(
        f"/api/v1/test-suites/{test_suite['id']}",
        headers=other_headers,
    )

    assert response.status_code == 404


def test_test_suite_name_cannot_be_blank(client: TestClient) -> None:
    headers = create_user_headers(client, "suite.owner@example.com")
    project = create_project(client, headers)

    response = client.post(
        f"/api/v1/projects/{project['id']}/test-suites",
        headers=headers,
        json={"name": "   "},
    )

    assert response.status_code == 422


def test_delete_owned_test_suite(client: TestClient) -> None:
    headers = create_user_headers(client, "delete.suite@example.com")
    project = create_project(client, headers)
    test_suite = create_test_suite(client, headers, project["id"])

    response = client.delete(
        f"/api/v1/test-suites/{test_suite['id']}", headers=headers
    )

    assert response.status_code == 204
    assert client.get(
        f"/api/v1/test-suites/{test_suite['id']}", headers=headers
    ).status_code == 404


def test_cannot_delete_another_users_test_suite(client: TestClient) -> None:
    owner_headers = create_user_headers(client, "delete.suite.owner@example.com")
    project = create_project(client, owner_headers)
    test_suite = create_test_suite(client, owner_headers, project["id"])
    other_headers = create_user_headers(client, "delete.suite.other@example.com")

    response = client.delete(
        f"/api/v1/test-suites/{test_suite['id']}", headers=other_headers
    )

    assert response.status_code == 404
