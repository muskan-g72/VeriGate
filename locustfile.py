import os
import requests
from locust import HttpUser, task, between, events

BEARER_TOKEN = None
PROJECT_ID = os.getenv("LOADTEST_PROJECT_ID", "686228c2-4af8-40b9-a240-96af2d6300b3")

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Authenticate ONCE at test initialization and share Bearer token across all virtual users."""
    global BEARER_TOKEN
    base_url = environment.host or "http://127.0.0.1:8000"
    username = os.getenv("LOADTEST_USER", "loadtest.user@example.com")
    password = os.getenv("LOADTEST_PASSWORD", "StrongPassword123!")

    try:
        resp = requests.post(
            f"{base_url.rstrip('/')}/api/v1/auth/login",
            data={"username": username, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
        if resp.status_code == 200:
            BEARER_TOKEN = resp.json().get("access_token")
            print(f"[test_start] Authenticated successfully as {username}")
        else:
            print(f"[test_start] Login failed ({resp.status_code}): {resp.text}")
    except Exception as exc:
        print(f"[test_start] Exception during initial login: {exc}")

class VeriGateUser(HttpUser):
    wait_time = between(1.0, 2.0)

    def on_start(self):
        """Assign pre-fetched Bearer token so bcrypt hashing is not measured during the test."""
        if BEARER_TOKEN:
            self.client.headers["Authorization"] = f"Bearer {BEARER_TOKEN}"

    @task(3)
    def get_dashboard_summary(self):
        """Fetch aggregated metrics for projects, test suites, cases, and runs."""
        self.client.get("/api/v1/dashboard/summary", name="/api/v1/dashboard/summary")

    @task(3)
    def list_projects(self):
        """Fetch list of user projects from PostgreSQL."""
        self.client.get("/api/v1/projects", name="/api/v1/projects")

    @task(2)
    def get_profile(self):
        """Fetch authenticated user profile."""
        self.client.get("/api/v1/auth/me", name="/api/v1/auth/me")

    @task(2)
    def get_project_reports(self):
        """Fetch verification reports for a seeded project."""
        self.client.get(f"/api/v1/projects/{PROJECT_ID}/reports", name="/api/v1/projects/[id]/reports")

    @task(1)
    def get_health(self):
        """Public health check baseline endpoint."""
        self.client.get("/api/v1/health", name="/api/v1/health")
