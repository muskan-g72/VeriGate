from fastapi.testclient import TestClient

PROJECTS_URL = "/api/v1/projects"


def authentication_headers(
    client: TestClient,
    email: str = "project.owner@example.com",
) -> dict[str, str]:
    password = "StrongPassword123!"
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Project Owner",
        },
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_project(
    client: TestClient,
    headers: dict[str, str],
) -> dict[str, object]:
    response = client.post(
        PROJECTS_URL,
        headers=headers,
        json={
            "name": "Backend Verification",
            "description": "Verify the VeriGate API.",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_create_project(client: TestClient) -> None:
    headers = authentication_headers(client)
    project = create_project(client, headers)

    assert project["name"] == "Backend Verification"
    assert project["description"] == "Verify the VeriGate API."
    assert project["owner_id"]
    assert project["id"]


def test_projects_require_authentication(client: TestClient) -> None:
    response = client.get(PROJECTS_URL)

    assert response.status_code == 401


def test_list_projects_returns_only_current_users_projects(
    client: TestClient,
) -> None:
    owner_headers = authentication_headers(client)
    owned_project = create_project(client, owner_headers)

    other_headers = authentication_headers(client, "other.owner@example.com")
    create_project(client, other_headers)

    response = client.get(PROJECTS_URL, headers=owner_headers)

    assert response.status_code == 200
    assert [project["id"] for project in response.json()] == [owned_project["id"]]


def test_read_owned_project(client: TestClient) -> None:
    headers = authentication_headers(client)
    project = create_project(client, headers)

    response = client.get(f"{PROJECTS_URL}/{project['id']}", headers=headers)

    assert response.status_code == 200
    assert response.json()["id"] == project["id"]


def test_update_owned_project(client: TestClient) -> None:
    headers = authentication_headers(client)
    project = create_project(client, headers)

    response = client.patch(
        f"{PROJECTS_URL}/{project['id']}",
        headers=headers,
        json={"name": "Updated Project", "description": None},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Project"
    assert response.json()["description"] is None


def test_user_cannot_read_another_users_project(client: TestClient) -> None:
    owner_headers = authentication_headers(client)
    project = create_project(client, owner_headers)
    other_headers = authentication_headers(client, "other.owner@example.com")

    response = client.get(
        f"{PROJECTS_URL}/{project['id']}",
        headers=other_headers,
    )

    assert response.status_code == 404


def test_user_cannot_update_another_users_project(client: TestClient) -> None:
    owner_headers = authentication_headers(client)
    project = create_project(client, owner_headers)
    other_headers = authentication_headers(client, "other.owner@example.com")

    response = client.patch(
        f"{PROJECTS_URL}/{project['id']}",
        headers=other_headers,
        json={"name": "Unauthorized update"},
    )

    assert response.status_code == 404


def test_project_name_cannot_be_blank(client: TestClient) -> None:
    headers = authentication_headers(client)
    response = client.post(
        PROJECTS_URL,
        headers=headers,
        json={"name": "   ", "description": None},
    )

    assert response.status_code == 422
