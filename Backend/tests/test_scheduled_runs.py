import uuid

from fastapi.testclient import TestClient


def headers(client: TestClient):
    email = f"schedule_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/v1/auth/register", json={"email": email, "password": "StrongPassword123!", "full_name": "Schedule User"})
    response = client.post("/api/v1/auth/login", data={"username": email, "password": "StrongPassword123!"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_create_pause_and_list_scheduled_run(client: TestClient):
    auth = headers(client)
    project = client.post("/api/v1/projects", headers=auth, json={"name": "Scheduled project"}).json()
    suite = client.post(f"/api/v1/projects/{project['id']}/test-suites", headers=auth, json={"name": "Nightly suite"}).json()
    created = client.post(f"/api/v1/test-suites/{suite['id']}/scheduled-runs", headers=auth, json={"name": "Nightly", "interval_minutes": 1440}).json()
    assert created["enabled"] is True and created["interval_minutes"] == 1440
    paused = client.patch(f"/api/v1/scheduled-runs/{created['id']}", headers=auth, json={"enabled": False})
    assert paused.status_code == 200 and paused.json()["enabled"] is False
    listed = client.get(f"/api/v1/test-suites/{suite['id']}/scheduled-runs", headers=auth)
    assert listed.status_code == 200 and len(listed.json()) == 1
