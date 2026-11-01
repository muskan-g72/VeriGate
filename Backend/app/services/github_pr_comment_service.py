"""Safe, deterministic publication of one updatable GitHub PR summary comment."""
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.github_pr_comment import GitHubPrComment
from app.models.project import Project
from app.models.verification_run import VerificationRun
from app.services.github_service import create_github_pr_comment, find_github_pr_comment, update_github_pr_comment
from app.services.report_generator import sanitize_report_text

MAX_COMMENT_LENGTH = 60_000


def _clean(value: object, limit: int = 500) -> str:
    text = sanitize_report_text(str(value or "")) or ""
    text = re.sub(r"[\x00-\x1f\x7f]", " ", text)
    text = re.sub(r"([`*_{}\[\]()<>#+!|])", r"\\\1", text)
    text = re.sub(
        r"\\\[(REDACTED(?:\\_TOKEN|\\_JWT)?)\\\]",
        lambda match: f"[{match.group(1).replace(r'\_', '_')}]",
        text,
    )
    return text.strip()[:limit]


def build_pr_comment(run: VerificationRun, project: Project, analyses: dict | None = None) -> str:
    marker = f"<!-- verigate:run-comment project={project.id} -->"
    evaluation = run.quality_gate_evaluation
    outcome = evaluation.outcome if evaluation and evaluation.outcome in {"passed", "failed"} else ("failed" if run.failed_count or run.blocked_count else "passed")
    icon = "✅" if outcome == "passed" else "❌"
    completed = run.passed_count + run.failed_count + run.blocked_count + run.skipped_count
    rate = round(run.passed_count / completed * 100, 1) if completed else 0
    lines = [marker, f"## {icon} VeriGate verification {outcome}", f"**Results:** {run.passed_count} passed · {run.failed_count} failed · {run.blocked_count} blocked · {run.skipped_count} skipped · **{rate}% pass rate**"]
    if evaluation:
        lines += ["", "### Quality gate", "| Rule | Measured | Threshold | Result | Reason |", "| --- | ---: | ---: | --- | --- |"]
        for rule in evaluation.rule_results or []:
            suffix = "%" if rule.get("rule") == "min_pass_rate" else ""
            lines.append(f"| {_clean(rule.get('rule'))} | {_clean(rule.get('measured_value'))}{suffix} | {_clean(rule.get('threshold'))}{suffix} | {'✅ Passed' if rule.get('passed') else '❌ Failed'} | {_clean(rule.get('reason'))} |")
    failed = [result for result in run.results if result.status in {"failed", "blocked"}]
    if failed:
        lines += ["", "### Failed or blocked tests"]
        shown = failed[:project.comment_max_failures]
        for result in shown:
            case = result.test_case
            title = _clean(case.title if case else f"Test case {result.test_case_id}")
            lines.append(f"- **{title}** — {_clean(result.failure_message or 'No failure message recorded.', 300)}")
            diagnosis = (analyses or {}).get(str(result.id)) if project.comment_include_ai else None
            if diagnosis:
                lines.append(f"  - Root cause: {_clean(diagnosis.root_cause, 350)}")
                lines.append(f"  - Suggested fix: {_clean(diagnosis.suggested_fix, 350)}")
        if len(failed) > len(shown):
            lines.append(f"- …and {len(failed) - len(shown)} more. See the run for details.")
        if project.comment_include_ai and not analyses:
            lines.append("- AI analysis was unavailable; see the run for details.")
    run_url = f"{settings.frontend_url.rstrip('/')}/app/verification-runs/{run.id}"
    timestamp = getattr(run, "completed_at", None) or getattr(run, "created_at", None)
    timestamp_text = timestamp.isoformat() if timestamp else "completion time unavailable"
    lines += ["", f"[Open verification run]({run_url}) · Run `{run.id}` · Commit `{(run.pr_commit_sha or '')[:7]}` · {timestamp_text}"]
    body = "\n".join(lines)
    return body[:MAX_COMMENT_LENGTH]


async def publish_pr_comment(database_session: Session, run: VerificationRun, project: Project, analyses: dict | None = None) -> None:
    if not project.pr_comments_enabled or not run.pr_repository or not run.pr_number:
        return
    marker = f"<!-- verigate:run-comment project={project.id} -->"
    token = getattr(project, "github_token", None)
    body = build_pr_comment(run, project, analyses)
    record = database_session.scalar(select(GitHubPrComment).where(GitHubPrComment.project_id == project.id, GitHubPrComment.repository == run.pr_repository, GitHubPrComment.pr_number == run.pr_number))
    if record is None:
        record = GitHubPrComment(project_id=project.id, repository=run.pr_repository, pr_number=run.pr_number)
        database_session.add(record)
        database_session.flush()
    response = None
    status = ""
    error = ""
    if record.github_comment_id:
        response, status, error = await update_github_pr_comment(run.pr_repository, record.github_comment_id, body, token)
        if status == 404:
            found, _, _ = await find_github_pr_comment(run.pr_repository, run.pr_number, marker, token=token)
            if found:
                record.github_comment_id = found.get("id")
                response, status, error = await update_github_pr_comment(run.pr_repository, record.github_comment_id, body, token)
            else:
                response, status, error = await create_github_pr_comment(
                    run.pr_repository, run.pr_number, body, token
                )
    else:
        found, _, _ = await find_github_pr_comment(run.pr_repository, run.pr_number, marker, token=token)
        if found:
            record.github_comment_id = found.get("id")
            response, status, error = await update_github_pr_comment(run.pr_repository, record.github_comment_id, body, token)
        else:
            response, status, error = await create_github_pr_comment(run.pr_repository, run.pr_number, body, token)
    if response:
        record.github_comment_id = response.get("id", record.github_comment_id)
        record.comment_url = response.get("html_url", record.comment_url)
        record.last_status = "updated" if record.last_run_id else "posted"
        record.last_error = None
        run.comment_status, run.comment_url, run.comment_error = record.last_status, record.comment_url, None
    else:
        record.last_status = "failed"
        record.last_error = (
            sanitize_report_text(error) or "GitHub PR comment request failed"
        )[:400]
        run.comment_status, run.comment_error = "failed", record.last_error
    record.last_run_id = run.id
    database_session.commit()
