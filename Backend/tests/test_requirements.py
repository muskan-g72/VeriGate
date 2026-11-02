from datetime import UTC, datetime, timedelta
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import event, update

from app.models.verification_run import VerificationRun
from app.services.requirement_traceability_service import build_traceability_matrix


def headers(client: TestClient, email: str) -> dict[str, str]:
    assert client.post("/api/v1/auth/register", json={"email": email, "password": "StrongPassword123!", "full_name": "Requirement User"}).status_code == 201
    response = client.post("/api/v1/auth/login", data={"username": email, "password": "StrongPassword123!"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def project(client: TestClient, auth: dict[str, str], name: str = "RTM Project") -> dict:
    response = client.post("/api/v1/projects", headers=auth, json={"name": name})
    assert response.status_code == 201
    return response.json()


def suite(client: TestClient, auth: dict[str, str], project_id: str, name: str) -> dict:
    response = client.post(f"/api/v1/projects/{project_id}/test-suites", headers=auth, json={"name": name})
    assert response.status_code == 201
    return response.json()


def case(client: TestClient, auth: dict[str, str], suite_id: str, title: str) -> dict:
    response = client.post(f"/api/v1/test-suites/{suite_id}/test-cases", headers=auth, json={"title": title, "steps": "Execute", "expected_result": "Pass"})
    assert response.status_code == 201
    return response.json()


def completed_run(client: TestClient, auth: dict[str, str], suite_id: str, result_status: str) -> tuple[dict, dict]:
    response = client.post(f"/api/v1/test-suites/{suite_id}/verification-runs", headers=auth, json={"name": "RTM verification"})
    assert response.status_code == 201
    run = response.json()
    assert len(run["results"]) == 1
    result = run["results"][0]
    response = client.patch(f"/api/v1/verification-results/{result['id']}", headers=auth, json={"status": result_status})
    assert response.status_code == 200
    return run, response.json()


def requirement(client: TestClient, auth: dict[str, str], project_id: str, key: str = "REQ-001", **overrides) -> dict:
    payload = {"requirement_key": key, "title": "Account access", "source": "internal://specification", **overrides}
    response = client.post(f"/api/v1/projects/{project_id}/requirements", headers=auth, json=payload)
    assert response.status_code == 201
    return response.json()


def test_requirement_crud_permissions_deprecation_and_audit(client: TestClient) -> None:
    owner = headers(client, "rtm.owner@example.com")
    viewer = headers(client, "rtm.viewer@example.com")
    item = project(client, owner)
    viewer_id = client.get("/api/v1/auth/me", headers=viewer).json()["id"]
    assert client.post(f"/api/v1/projects/{item['id']}/members", headers=owner, json={"user_id": viewer_id, "role": "viewer"}).status_code == 201

    created = requirement(client, owner, item["id"])
    duplicate = client.post(f"/api/v1/projects/{item['id']}/requirements", headers=owner, json={"requirement_key": "REQ-001", "title": "Duplicate"})
    assert duplicate.status_code == 409
    assert client.get(f"/api/v1/projects/{item['id']}/requirements", headers=viewer).status_code == 200
    assert client.post(f"/api/v1/projects/{item['id']}/requirements", headers=viewer, json={"requirement_key": "REQ-002", "title": "No access"}).status_code == 403

    deprecated = client.patch(f"/api/v1/requirements/{created['id']}", headers=owner, json={"status": "deprecated"})
    assert deprecated.status_code == 200
    assert client.get(f"/api/v1/projects/{item['id']}/requirements", headers=owner).json() == []
    assert [row["id"] for row in client.get(f"/api/v1/projects/{item['id']}/requirements?include_deprecated=true", headers=owner).json()] == [created["id"]]
    assert client.get(f"/api/v1/projects/{item['id']}/requirements/traceability", headers=owner).json()["items"] == []
    assert client.patch(f"/api/v1/requirements/{created['id']}", headers=viewer, json={"title": "No permission"}).status_code == 403
    audit = client.get(f"/api/v1/audit-logs?project_id={item['id']}&resource_type=requirement", headers=owner).json()
    assert {row["action"] for row in audit} >= {"created", "deprecated"}
    assert all("internal://specification" not in (row["description"] or "") for row in audit)


def test_requirement_test_case_linking_preserves_history_and_isolated(client: TestClient) -> None:
    owner = headers(client, "rtm.links@example.com")
    first_project = project(client, owner, "First RTM Project")
    first_suite = suite(client, owner, first_project["id"], "First suite")
    first_case = case(client, owner, first_suite["id"], "First case")
    item = requirement(client, owner, first_project["id"])
    _, result = completed_run(client, owner, first_suite["id"], "passed")

    assert client.post(f"/api/v1/requirements/{item['id']}/test-cases/{first_case['id']}", headers=owner).status_code == 200
    assert client.post(f"/api/v1/requirements/{item['id']}/test-cases/{first_case['id']}", headers=owner).status_code == 409
    assert client.delete(f"/api/v1/requirements/{item['id']}/test-cases/{first_case['id']}", headers=owner).status_code == 204
    assert client.get(f"/api/v1/verification-results/{result['id']}", headers=owner).status_code == 200

    second_project = project(client, owner, "Second RTM Project")
    second_suite = suite(client, owner, second_project["id"], "Second suite")
    second_case = case(client, owner, second_suite["id"], "Second case")
    cross_project = client.post(f"/api/v1/requirements/{item['id']}/test-cases/{second_case['id']}", headers=owner)
    assert cross_project.status_code == 422
    audit = client.get(f"/api/v1/audit-logs?project_id={first_project['id']}&resource_type=requirement_test_case", headers=owner).json()
    assert {row["action"] for row in audit} == {"linked", "unlinked"}


def test_requirement_issue_links_are_project_scoped(client: TestClient) -> None:
    owner = headers(client, "rtm.issues@example.com")
    item = project(client, owner)
    owned_suite = suite(client, owner, item["id"], "Issue suite")
    case(client, owner, owned_suite["id"], "Broken test")
    req = requirement(client, owner, item["id"])
    _, failed_result = completed_run(client, owner, owned_suite["id"], "failed")
    issue_response = client.post(f"/api/v1/verification-results/{failed_result['id']}/issues", headers=owner, json={"title": "Broken requirement"})
    assert issue_response.status_code == 201
    issue = issue_response.json()
    assert client.post(f"/api/v1/requirements/{req['id']}/issues/{issue['id']}", headers=owner).status_code == 200
    assert client.delete(f"/api/v1/requirements/{req['id']}/issues/{issue['id']}", headers=owner).status_code == 204

    other_project = project(client, owner, "Other issue project")
    other_suite = suite(client, owner, other_project["id"], "Other suite")
    case(client, owner, other_suite["id"], "Other broken test")
    _, other_failed = completed_run(client, owner, other_suite["id"], "failed")
    other_issue = client.post(f"/api/v1/verification-results/{other_failed['id']}/issues", headers=owner, json={"title": "Other issue"}).json()
    assert client.post(f"/api/v1/requirements/{req['id']}/issues/{other_issue['id']}", headers=owner).status_code == 422


def test_traceability_uses_latest_completed_result_per_case_across_suites_and_batches_queries(client: TestClient, db_session) -> None:
    owner = headers(client, "rtm.matrix@example.com")
    item = project(client, owner)
    suite_a = suite(client, owner, item["id"], "Authentication")
    suite_b = suite(client, owner, item["id"], "Payments")
    case_a = case(client, owner, suite_a["id"], "Login works")
    case_b = case(client, owner, suite_b["id"], "Payment works")
    req = requirement(client, owner, item["id"], status="approved")
    assert client.post(f"/api/v1/requirements/{req['id']}/test-cases/{case_a['id']}", headers=owner).status_code == 200
    assert client.post(f"/api/v1/requirements/{req['id']}/test-cases/{case_b['id']}", headers=owner).status_code == 200

    old_run, old_result = completed_run(client, owner, suite_a["id"], "failed")
    new_run, _ = completed_run(client, owner, suite_a["id"], "passed")
    second_run, second_result = completed_run(client, owner, suite_b["id"], "skipped")
    now = datetime.now(UTC)
    db_session.execute(update(VerificationRun).where(VerificationRun.id == uuid.UUID(old_run["id"])).values(completed_at=now - timedelta(minutes=2)))
    db_session.execute(update(VerificationRun).where(VerificationRun.id == uuid.UUID(new_run["id"])).values(completed_at=now - timedelta(minutes=1)))
    db_session.execute(update(VerificationRun).where(VerificationRun.id == uuid.UUID(second_run["id"])).values(completed_at=now))
    db_session.commit()

    issue = client.post(f"/api/v1/verification-results/{old_result['id']}/issues", headers=owner, json={"title": "Historical payment issue"}).json()
    assert client.post(f"/api/v1/requirements/{req['id']}/issues/{issue['id']}", headers=owner).status_code == 200
    statements: list[str] = []
    def count_queries(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)
    event.listen(db_session.bind, "before_cursor_execute", count_queries)
    try:
        matrix = build_traceability_matrix(db_session, item["id"])
    finally:
        event.remove(db_session.bind, "before_cursor_execute", count_queries)
    row = matrix["items"][0]
    statuses = {str(test["id"]): test["latest_status"] for test in row["test_cases"]}
    assert statuses == {case_a["id"]: "passed", case_b["id"]: "skipped"}
    assert row["coverage_status"] == "not_passing"
    assert row["passing_test_case_count"] == 1
    assert row["not_passing_test_case_count"] == 1
    assert row["unresolved_issue_count"] == 1
    assert len(statements) <= 7
    exported = client.get(f"/api/v1/projects/{item['id']}/requirements/traceability.csv", headers=owner)
    assert exported.status_code == 200
    assert "REQ-001" in exported.text
