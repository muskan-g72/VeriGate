import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.services import github_service
from app.services.github_pr_comment_service import MAX_COMMENT_LENGTH, _clean, build_pr_comment, publish_pr_comment
from app.models.github_pr_comment import GitHubPrComment
from app.services.report_generator import sanitize_report_text


def make_run(*, failures=0, gate=None, message="AssertionError: password=SuperSecret123!"):
    results = [SimpleNamespace(id=uuid.uuid4(), status="failed", failure_message=message, test_case=SimpleNamespace(title="<script>alert(1)</script>")) for _ in range(failures)]
    return SimpleNamespace(
        id=uuid.uuid4(), pr_commit_sha="abcdef123456", results=results,
        passed_count=2, failed_count=failures, blocked_count=0, skipped_count=0,
        quality_gate_evaluation=gate,
    )


def make_project(**overrides):
    values = {"id": uuid.uuid4(), "comment_max_failures": 10, "comment_include_ai": True}
    values.update(overrides)
    return SimpleNamespace(**values)


def test_comment_builder_marker_gate_redaction_and_ai_opt_in():
    gate = SimpleNamespace(outcome="failed", rule_results=[{"rule": "min_pass_rate", "measured_value": 40, "threshold": 80, "passed": False, "reason": "Below threshold"}])
    run, project = make_run(failures=1, gate=gate), make_project()
    diagnosis = SimpleNamespace(root_cause="Credentials were rejected", suggested_fix="Rotate the test credential")
    body = build_pr_comment(run, project, {str(run.results[0].id): diagnosis})
    assert body == build_pr_comment(run, project, {str(run.results[0].id): diagnosis})
    assert f"<!-- verigate:run-comment project={project.id} -->" in body
    assert r"| min\_pass\_rate | 40% | 80% |" in body
    assert "SuperSecret123!" not in body and "[REDACTED]" in body
    assert "\\<script\\>" in body
    assert "Root cause: Credentials were rejected" in body
    project.comment_include_ai = False
    assert "Root cause:" not in build_pr_comment(run, project, {str(run.results[0].id): diagnosis})


def test_comment_builder_cap_and_total_size_limit():
    run, project = make_run(failures=25, message="x" * 10_000), make_project(comment_max_failures=3)
    body = build_pr_comment(run, project)
    assert body.count("**\\<script\\>") == 3
    assert "and 22 more" in body
    assert len(body) <= MAX_COMMENT_LENGTH


def test_comment_builder_redacts_each_user_derived_text_field():
    fake_secret = "github_pat_FAKEVALUE123!"
    gate = SimpleNamespace(
        outcome="failed",
        rule_results=[{
            "rule": "min_pass_rate",
            "measured_value": 40,
            "threshold": 80,
            "passed": False,
            "reason": f"secret={fake_secret}",
        }],
    )
    run = make_run(failures=1, gate=gate, message=f"token={fake_secret}")
    run.pr_title = fake_secret
    run.results[0].test_case.title = f"Authorization: Bearer {fake_secret}"
    diagnosis = SimpleNamespace(
        root_cause=f"password={fake_secret}",
        suggested_fix=f"api_key={fake_secret}",
    )

    body = build_pr_comment(run, make_project(), {str(run.results[0].id): diagnosis})

    assert fake_secret not in body.replace("\\", "")
    assert body.count("[REDACTED]") >= 4
    assert "[REDACTED_TOKEN]" in body


def test_report_and_comment_keep_typed_redaction_markers():
    jwt = "eyFAKEVALUE123.eyFAKEVALUE456.FAKEVALUE789"
    values = {
        "Bearer fake-token!": "[REDACTED_TOKEN]",
        jwt: "[REDACTED_JWT]",
        "password=fake-value!": "[REDACTED]",
        "secret=fake-value!": "[REDACTED]",
    }
    for value, placeholder in values.items():
        assert placeholder in (sanitize_report_text(value) or "")
        assert placeholder in _clean(value)


def test_comment_requests_retry_only_once_for_5xx(monkeypatch):
    monkeypatch.setattr(github_service.settings, "github_token", "test-token")
    calls = []

    async def fake_request(*_args, **_kwargs):
        calls.append(1)
        return None, 500, "server error"

    with patch("app.services.github_service._comment_request", new=AsyncMock(side_effect=fake_request)):
        # The public helper delegates once; transport retries remain contained in _comment_request.
        result = asyncio.run(github_service.create_github_pr_comment("org/repo", 7, "body"))
    assert result == (None, 500, "server error") and len(calls) == 1


def test_marker_discovery_and_permission_failure_are_non_posting(monkeypatch):
    monkeypatch.setattr(github_service.settings, "github_token", "test-token")
    marker = "<!-- verigate:run-comment project=abc -->"
    with patch("app.services.github_service._comment_request", new=AsyncMock(return_value=([{"id": 8, "body": marker}], 200, ""))):
        found, status, error = asyncio.run(github_service.find_github_pr_comment("org/repo", 1, marker))
    assert found["id"] == 8 and status == 200 and not error
    with patch("app.services.github_service._comment_request", new=AsyncMock(return_value=(None, 403, "forbidden"))):
        response, status, error = asyncio.run(github_service.create_github_pr_comment("org/repo", 1, "body"))
    assert response is None and status == 403 and "forbidden" in error


class FakeSession:
    def __init__(self, record=None):
        self.record = record

    def scalar(self, _query):
        return self.record

    def add(self, record):
        self.record = record

    def flush(self):
        pass

    def commit(self):
        pass


def comment_run():
    return SimpleNamespace(
        id=uuid.uuid4(), pr_repository="owner/repo", pr_number=13,
        pr_commit_sha="abc123", results=[], passed_count=1, failed_count=0,
        blocked_count=0, skipped_count=0, quality_gate_evaluation=None,
        comment_status=None, comment_url=None, comment_error=None,
    )


def test_publish_comment_creates_then_updates_without_duplicate():
    project = make_project(pr_comments_enabled=True)
    run = comment_run()
    session = FakeSession()
    created = {"id": 91, "html_url": "https://github.test/comment/91"}
    with patch("app.services.github_pr_comment_service.find_github_pr_comment", new=AsyncMock(return_value=(None, 404, ""))), patch("app.services.github_pr_comment_service.create_github_pr_comment", new=AsyncMock(return_value=(created, 201, ""))) as create:
        asyncio.run(publish_pr_comment(session, run, project))
    assert create.await_count == 1
    assert session.record.github_comment_id == 91

    next_run = comment_run()
    with patch("app.services.github_pr_comment_service.update_github_pr_comment", new=AsyncMock(return_value=(created, 200, ""))) as update:
        asyncio.run(publish_pr_comment(session, next_run, project))
    assert update.await_count == 1
    assert next_run.comment_status == "updated"


def test_stale_comment_id_falls_back_to_create():
    project = make_project(pr_comments_enabled=True)
    record = GitHubPrComment(
        project_id=project.id, repository="owner/repo", pr_number=13,
        github_comment_id=90, last_status="posted",
    )
    session = FakeSession(record)
    created = {"id": 92, "html_url": "https://github.test/comment/92"}
    with patch("app.services.github_pr_comment_service.update_github_pr_comment", new=AsyncMock(return_value=(None, 404, "missing"))), patch("app.services.github_pr_comment_service.find_github_pr_comment", new=AsyncMock(return_value=(None, 404, ""))), patch("app.services.github_pr_comment_service.create_github_pr_comment", new=AsyncMock(return_value=(created, 201, ""))) as create:
        asyncio.run(publish_pr_comment(session, comment_run(), project))
    assert create.await_count == 1
    assert record.github_comment_id == 92
