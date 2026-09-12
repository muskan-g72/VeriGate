import json
import logging
import re
import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Header,
    HTTPException,
    Request,
    Response,
    status,
)
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import CurrentUser
from app.core.permissions import (
    VIEW_PROJECT_ROLES,
    get_accessible_project,
    is_system_admin,
    project_access_condition,
)
from app.db.session import get_db
from app.models.project import Project
from app.models.test_case import TestCase
from app.models.test_suite import TestSuite
from app.models.verification_result import VerificationResult
from app.models.verification_run import VerificationRun
from app.schemas.verification import VerificationRunRead
from app.services.github_pr_verifier import run_github_pr_verification
from app.services.github_service import verify_github_signature

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/github", tags=["GitHub"])


def normalize_github_repo(raw: str | None) -> str | None:
    if not raw:
        return None
    cleaned = raw.strip()
    cleaned = re.sub(r"^https?://[^/]+/", "", cleaned)
    cleaned = re.sub(r"^git@[^:]+:", "", cleaned)
    cleaned = re.sub(r"\.git$", "", cleaned)
    return cleaned.strip("/")


@router.post(
    "/webhook",
    status_code=status.HTTP_202_ACCEPTED,
    summary="GitHub Webhook Receiver",
    description="Receives GitHub pull_request webhook events, validates HMAC-SHA256 signature, creates an associated VerificationRun, and triggers background Playwright verification with screenshot evidence and AI root-cause diagnosis.",
)
async def github_webhook(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    database_session: Annotated[Session, Depends(get_db)],
    x_github_event: Annotated[str | None, Header()] = None,
    x_hub_signature_256: Annotated[str | None, Header()] = None,
    x_github_delivery: Annotated[str | None, Header()] = None,
):
    """
    Handle GitHub Webhook events (pull_request opened, synchronize, reopened).
    Validates HMAC signature, creates an associated VerificationRun, and triggers
    asynchronous verification in background tasks.
    """
    payload_bytes = await request.body()

    # 1. Handle ping event
    if x_github_event == "ping":
        response.status_code = status.HTTP_200_OK
        return {
            "status": "pong",
            "message": "VeriGate GitHub webhook receiver active.",
        }

    # 2. Only process pull_request events
    if x_github_event != "pull_request":
        response.status_code = status.HTTP_200_OK
        return {
            "status": "ignored",
            "reason": f"Event '{x_github_event}' is not supported.",
        }

    # 3. Parse JSON payload
    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed JSON payload: {exc}",
        )

    # 4. Resolve repository full name
    repo_data = payload.get("repository") or {}
    repo_full_name = repo_data.get("full_name")
    if not repo_full_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload missing repository full_name.",
        )

    # 5. Find matching VeriGate projects (all enabled projects configured for this repo)
    normalized_repo = normalize_github_repo(repo_full_name) or repo_full_name
    projects = list(
        database_session.scalars(
            select(Project)
            .where(
                or_(
                    func.lower(Project.github_repo) == repo_full_name.lower(),
                    func.lower(Project.github_repo) == normalized_repo.lower(),
                    Project.github_repo.ilike(f"%{normalized_repo}%"),
                )
            )
            .order_by(Project.github_verification_enabled.desc(), Project.created_at)
        )
    )

    if not projects:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No VeriGate project configured for repository '{repo_full_name}'.",
        )

    # 6. Verify HMAC-SHA256 signature against matching project secrets or global settings secret
    is_valid = any(
        verify_github_signature(
            payload_bytes=payload_bytes,
            signature_header=x_hub_signature_256,
            secret=p.github_webhook_secret,
        )
        for p in projects
    ) or verify_github_signature(
        payload_bytes=payload_bytes,
        signature_header=x_hub_signature_256,
        secret=None,
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid GitHub webhook signature.",
        )

    # Filter to projects with GitHub verification enabled
    enabled_projects = [p for p in projects if p.github_verification_enabled]
    if not enabled_projects:
        response.status_code = status.HTTP_200_OK
        return {
            "status": "ignored",
            "reason": "GitHub verification is disabled for configured project(s).",
        }

    # 7. Check action type (opened, synchronize, reopened)
    action = payload.get("action")
    if action not in {"opened", "synchronize", "reopened"}:
        response.status_code = status.HTTP_200_OK
        return {
            "status": "ignored",
            "reason": f"PR action '{action}' does not trigger verification.",
        }

    # 8. Extract Pull Request metadata
    pr_data = payload.get("pull_request") or {}
    pr_number = pr_data.get("number")
    pr_title = pr_data.get("title") or "Pull Request"
    pr_author = (pr_data.get("user") or {}).get("login")
    head = pr_data.get("head") or {}
    base = pr_data.get("base") or {}
    head_sha = head.get("sha")
    source_branch = head.get("ref")
    target_branch = base.get("ref")
    pr_url = pr_data.get("html_url")

    if not head_sha or not pr_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing pull request number or head commit SHA.",
        )

    short_sha = head_sha[:7]
    run_name = f"PR #{pr_number}: {pr_title[:70]} ({short_sha})"

    processed_runs: list[VerificationRun] = []

    # 9. Create or update VerificationRun for all enabled projects linked to this repo
    for project in enabled_projects:
        try:
            # Determine or auto-initialize Test Suite for this project
            suites = list(
                database_session.scalars(
                    select(TestSuite)
                    .where(TestSuite.project_id == project.id)
                    .order_by(TestSuite.created_at)
                )
            )
            if not suites:
                default_suite = TestSuite(
                    project_id=project.id,
                    name="PR Verification Suite",
                    description="Automated verification test suite for GitHub pull requests",
                )
                database_session.add(default_suite)
                database_session.flush()

                default_case = TestCase(
                    test_suite_id=default_suite.id,
                    title=f"Verify Example Domain - PR #{pr_number}",
                    description="Automated Playwright test for GitHub pull request verification",
                    steps="1. Navigate to https://example.com\n2. Verify page title is 'Example Domain'",
                    execution_mode="automated",
                    automation_steps=[
                        {"action": "goto", "value": "https://example.com"},
                        {"action": "expect_title", "value": "Example Domain"},
                    ],
                    expected_result="Page loads and title matches Example Domain",
                    priority="high",
                )
                database_session.add(default_case)
                database_session.flush()
                selected_suite = default_suite
                selected_cases = [default_case]
            else:
                # Select suite with active automated cases or fallback to first suite
                selected_suite = None
                selected_cases = []
                for suite in suites:
                    cases = list(
                        database_session.scalars(
                            select(TestCase)
                            .where(
                                TestCase.test_suite_id == suite.id,
                                TestCase.is_active.is_(True),
                            )
                            .order_by(TestCase.created_at)
                        )
                    )
                    if any(c.execution_mode == "automated" for c in cases):
                        selected_suite = suite
                        selected_cases = cases
                        break

                if not selected_suite:
                    selected_suite = suites[0]
                    selected_cases = list(
                        database_session.scalars(
                            select(TestCase)
                            .where(
                                TestCase.test_suite_id == selected_suite.id,
                                TestCase.is_active.is_(True),
                            )
                            .order_by(TestCase.created_at)
                        )
                    )

                if not selected_cases:
                    default_case = TestCase(
                        test_suite_id=selected_suite.id,
                        title=f"Verify Example Domain - PR #{pr_number}",
                        description="Automated Playwright test for GitHub pull request verification",
                        steps="1. Navigate to https://example.com\n2. Verify page title is 'Example Domain'",
                        execution_mode="automated",
                        automation_steps=[
                            {"action": "goto", "value": "https://example.com"},
                            {"action": "expect_title", "value": "Example Domain"},
                        ],
                        expected_result="Page loads and title matches Example Domain",
                        priority="high",
                    )
                    database_session.add(default_case)
                    database_session.flush()
                    selected_cases = [default_case]

            # 10. Check for existing PR verification run for this project and PR number
            idempotency_key = (
                f"github_pr:{project.id}:{repo_full_name}:{pr_number}:{head_sha}:{action}"
            )

            existing_run = database_session.scalar(
                select(VerificationRun)
                .join(TestSuite, VerificationRun.test_suite_id == TestSuite.id)
                .options(
                    selectinload(VerificationRun.results),
                    selectinload(VerificationRun.test_suite),
                )
                .where(
                    TestSuite.project_id == project.id,
                    VerificationRun.pr_number == pr_number,
                )
                .order_by(VerificationRun.created_at.desc())
            )

            if existing_run and existing_run.idempotency_key == idempotency_key:
                logger.info(
                    f"Duplicate delivery for project {project.name} PR #{pr_number}@{short_sha}:{action}"
                )
                response.status_code = status.HTTP_200_OK
                return {
                    "status": "duplicate",
                    "duplicate": True,
                    "verification_run_id": str(existing_run.id),
                    "run_id": str(existing_run.id),
                    "project_id": str(project.id),
                    "pr_number": pr_number,
                    "commit_sha": head_sha,
                    "message": "Verification run already triggered for this delivery.",
                }

            if existing_run:
                logger.info(
                    f"Updating existing PR verification run {existing_run.id} for project {project.name} on action '{action}'"
                )
                existing_run.name = run_name
                existing_run.status = "pending"
                existing_run.trigger_source = "github_pr"
                existing_run.pr_title = pr_title
                existing_run.pr_source_branch = source_branch
                existing_run.pr_target_branch = target_branch
                existing_run.pr_commit_sha = head_sha
                existing_run.pr_repository = repo_full_name
                existing_run.pr_author = pr_author
                existing_run.pr_url = pr_url
                existing_run.started_at = None
                existing_run.completed_at = None
                existing_run.idempotency_key = idempotency_key

                # Reset results to pending for new verification execution
                if existing_run.results:
                    for res in existing_run.results:
                        res.status = "pending"
                        res.actual_result = None
                        res.notes = None
                        res.executed_at = None
                else:
                    existing_run.results = [
                        VerificationResult(test_case_id=tc.id) for tc in selected_cases
                    ]

                verification_run = existing_run
            else:
                logger.info(
                    f"Creating new PR verification run for project {project.name} PR #{pr_number}"
                )
                verification_run = VerificationRun(
                    test_suite_id=selected_suite.id,
                    created_by_id=project.owner_id,
                    name=run_name,
                    status="pending",
                    trigger_source="github_pr",
                    pr_number=pr_number,
                    pr_title=pr_title,
                    pr_source_branch=source_branch,
                    pr_target_branch=target_branch,
                    pr_commit_sha=head_sha,
                    pr_repository=repo_full_name,
                    pr_author=pr_author,
                    pr_url=pr_url,
                    idempotency_key=idempotency_key,
                )
                verification_run.results = [
                    VerificationResult(test_case_id=tc.id) for tc in selected_cases
                ]

            database_session.add(verification_run)
            database_session.commit()
            database_session.refresh(verification_run)

            processed_runs.append(verification_run)

            # Queue asynchronous verification in background
            background_tasks.add_task(
                run_github_pr_verification, verification_run.id
            )
            logger.info(
                f"Successfully persisted and queued PR verification {verification_run.id} for project {project.name}"
            )

        except Exception as exc:
            database_session.rollback()
            logger.exception(
                f"Database error persisting GitHub PR verification for project '{project.name}' ({project.id}): {exc}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error persisting GitHub PR verification: {exc}",
            )

    primary_run = processed_runs[0]
    return {
        "status": "queued",
        "verification_run_id": str(primary_run.id),
        "run_id": str(primary_run.id),
        "project_id": str(enabled_projects[0].id),
        "pr_number": pr_number,
        "commit_sha": head_sha,
        "test_count": len(primary_run.results),
        "message": f"Verification run queued for PR #{pr_number}.",
    }


@router.get(
    "/pr-verifications",
    response_model=list[VerificationRunRead],
    summary="List GitHub PR Verifications",
    description="List all verification runs triggered by GitHub Pull Requests across accessible projects.",
)
def list_pr_verifications(
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
    project_id: uuid.UUID | None = None,
    limit: int = 50,
):
    """
    List all GitHub PR-triggered verification runs across accessible projects.
    """
    query = (
        select(VerificationRun)
        .join(TestSuite, VerificationRun.test_suite_id == TestSuite.id)
        .join(Project, TestSuite.project_id == Project.id)
        .options(
            selectinload(VerificationRun.results),
            selectinload(VerificationRun.test_suite),
        )
        .where(
            or_(
                VerificationRun.trigger_source == "github_pr",
                VerificationRun.pr_number.is_not(None),
            )
        )
    )

    if project_id:
        get_accessible_project(
            database_session,
            project_id,
            current_user,
            VIEW_PROJECT_ROLES,
        )
        query = query.where(TestSuite.project_id == project_id)
    else:
        if not is_system_admin(current_user):
            query = query.where(project_access_condition(current_user.id))

    runs = list(
        database_session.scalars(
            query.order_by(VerificationRun.created_at.desc()).limit(limit)
        )
    )
    return runs
