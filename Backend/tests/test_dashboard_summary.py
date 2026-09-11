import uuid

from fastapi.testclient import TestClient


def authenticated_headers(client: TestClient, email: str) -> dict[str, str]:
    password = "StrongPassword123!"
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Command User"},
    )
    assert reg.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_dashboard_summary_empty_workspace(client: TestClient):
    headers = authenticated_headers(client, "empty_workspace@example.com")
    resp = client.get("/api/v1/dashboard/summary", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_projects"] == 0
    assert data["total_test_suites"] == 0
    assert data["total_test_cases"] == 0
    assert data["total_runs"] == 0
    assert data["total_results"] == 0
    assert data["pass_rate"] == 0.0
    assert data["failure_rate"] == 0.0
    assert data["average_duration"] is None
    assert data["open_issues"] == 0
    assert data["health_score"] is None
    assert data["health_score_status"] == "unverified"
    assert data["recent_runs"] == []
    assert data["recent_failures"] == []
    assert data["trend"] == []


def test_dashboard_summary_with_runs_and_health_score(client: TestClient):
    headers = authenticated_headers(client, "metrics_user@example.com")

    # 1. Create Project
    p_resp = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "Command Project Alpha", "description": "Testing metrics"},
    )
    assert p_resp.status_code == 201
    project_id = p_resp.json()["id"]

    # 2. Create Test Suite
    s_resp = client.post(
        f"/api/v1/projects/{project_id}/test-suites",
        headers=headers,
        json={"name": "Smoke Suite"},
    )
    assert s_resp.status_code == 201
    suite_id = s_resp.json()["id"]

    # 3. Create 2 Test Cases
    tc1_resp = client.post(
        f"/api/v1/test-suites/{suite_id}/test-cases",
        headers=headers,
        json={
            "title": "TC 1 - Passing Case",
            "steps": "Step 1",
            "expected_result": "Success",
            "priority": "high",
            "execution_mode": "manual",
        },
    )
    assert tc1_resp.status_code == 201

    tc2_resp = client.post(
        f"/api/v1/test-suites/{suite_id}/test-cases",
        headers=headers,
        json={
            "title": "TC 2 - Failing Case",
            "steps": "Step 1",
            "expected_result": "Failure demo",
            "priority": "critical",
            "execution_mode": "manual",
        },
    )
    assert tc2_resp.status_code == 201

    # 4. Create a Verification Run
    run_resp = client.post(
        f"/api/v1/test-suites/{suite_id}/verification-runs",
        headers=headers,
        json={"name": "Run #1"},
    )
    assert run_resp.status_code == 201
    run = run_resp.json()
    run_id = run["id"]
    results = run["results"]
    assert len(results) == 2

    # 5. Update Results: 1 passed with duration 1.2s, 1 failed with duration 2.8s
    res1 = results[0]
    res2 = results[1]

    u1 = client.patch(
        f"/api/v1/verification-results/{res1['id']}",
        headers=headers,
        json={"status": "passed", "notes": "OK"},
    )
    assert u1.status_code == 200

    u2 = client.patch(
        f"/api/v1/verification-results/{res2['id']}",
        headers=headers,
        json={
            "status": "failed",
            "failure_message": "Network timeout after 5000ms",
            "stack_trace": "TimeoutError: Request exceeded 5000ms",
        },
    )
    assert u2.status_code == 200

    # 6. Fetch Dashboard Summary
    summary_resp = client.get("/api/v1/dashboard/summary", headers=headers)
    assert summary_resp.status_code == 200
    data = summary_resp.json()

    assert data["total_projects"] == 1
    assert data["total_test_suites"] == 1
    assert data["total_test_cases"] == 2
    assert data["total_runs"] == 1
    assert data["completed_runs"] == 1
    assert data["failed_runs"] == 1
    assert data["total_results"] == 2
    assert data["passed_results"] == 1
    assert data["failed_results"] == 1
    assert data["pass_rate"] == 50.0
    assert data["failure_rate"] == 50.0

    # Health score check:
    # pass_rate_points = (1 / 2) * 60 = 30
    # reliability_points = 25 - (1 * 5) = 20
    # defect_points = 15 - (0 * 3) = 15
    # total = 30 + 20 + 15 = 65 -> "degraded"
    assert data["health_score"] == 65
    assert data["health_score_status"] == "degraded"
    assert "health_breakdown" in data
    assert data["health_breakdown"]["pass_rate_points"] == 30.0
    assert data["health_breakdown"]["reliability_points"] == 20.0
    assert data["health_breakdown"]["defect_points"] == 15.0

    # Recent runs check
    assert len(data["recent_runs"]) == 1
    recent_run = data["recent_runs"][0]
    assert recent_run["id"] == run_id
    assert recent_run["name"] == "Run #1"
    assert recent_run["suite_name"] == "Smoke Suite"
    assert recent_run["project_name"] == "Command Project Alpha"
    assert recent_run["has_failures"] is True

    # Recent failures check
    assert len(data["recent_failures"]) == 1
    recent_fail = data["recent_failures"][0]
    assert recent_fail["result_id"] == str(res2["id"])
    assert "Network timeout" in recent_fail["failure_message"]
    assert recent_fail["run_id"] == str(run_id)

    # Trend check
    assert len(data["trend"]) >= 1
    point = data["trend"][-1]
    assert point["runs"] >= 1
    assert point["passed"] == 1
    assert point["failed"] == 1


def test_dashboard_summary_project_filter(client: TestClient):
    headers = authenticated_headers(client, "multiproject_user@example.com")

    # Project A
    p_a = client.post(
        "/api/v1/projects", headers=headers, json={"name": "Project A"}
    ).json()["id"]
    s_a = client.post(
        f"/api/v1/projects/{p_a}/test-suites",
        headers=headers,
        json={"name": "Suite A"},
    ).json()["id"]
    client.post(
        f"/api/v1/test-suites/{s_a}/test-cases",
        headers=headers,
        json={
            "title": "Case A",
            "steps": "Step",
            "expected_result": "Exp",
            "execution_mode": "manual",
        },
    )

    # Project B
    p_b = client.post(
        "/api/v1/projects", headers=headers, json={"name": "Project B"}
    ).json()["id"]
    s_b = client.post(
        f"/api/v1/projects/{p_b}/test-suites",
        headers=headers,
        json={"name": "Suite B"},
    ).json()["id"]
    client.post(
        f"/api/v1/test-suites/{s_b}/test-cases",
        headers=headers,
        json={
            "title": "Case B",
            "steps": "Step",
            "expected_result": "Exp",
            "execution_mode": "manual",
        },
    )

    # Filter to Project A
    resp_a = client.get(f"/api/v1/dashboard/summary?project_id={p_a}", headers=headers)
    assert resp_a.status_code == 200
    data_a = resp_a.json()
    assert data_a["total_projects"] == 1
    assert data_a["total_test_suites"] == 1
    assert data_a["total_test_cases"] == 1

    # Filter to Project B
    resp_b = client.get(f"/api/v1/dashboard/summary?project_id={p_b}", headers=headers)
    assert resp_b.status_code == 200
    data_b = resp_b.json()
    assert data_b["total_projects"] == 1
    assert data_b["total_test_suites"] == 1
    assert data_b["total_test_cases"] == 1

    # No filter (all accessible)
    resp_all = client.get("/api/v1/dashboard/summary", headers=headers)
    assert resp_all.status_code == 200
    data_all = resp_all.json()
    assert data_all["total_projects"] == 2
    assert data_all["total_test_suites"] == 2
    assert data_all["total_test_cases"] == 2


def test_dashboard_summary_unauthorized_and_foreign_project(client: TestClient):
    # 1. Unauthenticated request
    unauth = client.get("/api/v1/dashboard/summary")
    assert unauth.status_code == 401

    # 2. User 1 creates a project
    headers_u1 = authenticated_headers(client, "owner_u1@example.com")
    p1_id = client.post(
        "/api/v1/projects", headers=headers_u1, json={"name": "Private Project"}
    ).json()["id"]

    # 3. User 2 tries to access User 1's project via dashboard summary
    headers_u2 = authenticated_headers(client, "intruder_u2@example.com")
    forbidden = client.get(
        f"/api/v1/dashboard/summary?project_id={p1_id}", headers=headers_u2
    )
    assert forbidden.status_code in (403, 404)

    # 4. Random non-existent UUID
    missing = client.get(
        f"/api/v1/dashboard/summary?project_id={uuid.uuid4()}", headers=headers_u1
    )
    assert missing.status_code == 404
