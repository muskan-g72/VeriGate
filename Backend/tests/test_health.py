from fastapi.testclient import TestClient


def test_root(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Welcome to the VeriGate API",
        "documentation": "/docs",
    }


def test_application_health(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "VeriGate API",
    }


def test_database_health_uses_test_database(client: TestClient) -> None:
    response = client.get("/api/v1/health/database")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "database": "connected",
    }
