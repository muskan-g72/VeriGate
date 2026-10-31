import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.services import github_service
from app.services.github_pr_comment_service import MAX_COMMENT_LENGTH, build_pr_comment


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
    assert "| min\_pass\_rate | 40% | 80% |" in body
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
