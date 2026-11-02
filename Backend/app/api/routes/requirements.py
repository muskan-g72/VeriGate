import csv
import io
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import CurrentUser
from app.api.routes.issues import get_owned_issue
from app.api.routes.test_cases import get_owned_test_case
from app.core.permissions import MANAGE_TEST_ASSET_ROLES, VIEW_PROJECT_ROLES, get_accessible_project
from app.db.session import get_db
from app.models.requirement import Requirement
from app.schemas.requirement import RequirementCreate, RequirementRead, RequirementTraceabilityResponse, RequirementUpdate
from app.services.audit_service import record_audit_event
from app.services.requirement_traceability_service import build_traceability_matrix

router = APIRouter()
DatabaseSession = Annotated[Session, Depends(get_db)]


def get_owned_requirement(
    requirement_id: uuid.UUID,
    current_user: CurrentUser,
    database_session: Session,
    allowed_roles: tuple[str, ...] | None = None,
    *,
    with_links: bool = False,
) -> Requirement:
    query = select(Requirement).where(Requirement.id == requirement_id)
    if with_links:
        query = query.options(selectinload(Requirement.test_cases), selectinload(Requirement.issues))
    requirement = database_session.scalar(query)
    if requirement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requirement not found")
    get_accessible_project(database_session, requirement.project_id, current_user, allowed_roles or VIEW_PROJECT_ROLES)
    return requirement


@router.post("/projects/{project_id}/requirements", response_model=RequirementRead, status_code=status.HTTP_201_CREATED)
def create_requirement(project_id: uuid.UUID, payload: RequirementCreate, current_user: CurrentUser, database_session: DatabaseSession) -> Requirement:
    get_accessible_project(database_session, project_id, current_user, MANAGE_TEST_ASSET_ROLES)
    requirement = Requirement(project_id=project_id, created_by_id=current_user.id, **payload.model_dump())
    database_session.add(requirement)
    try:
        database_session.flush()
    except IntegrityError as exc:
        database_session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Requirement key already exists in this project") from exc
    record_audit_event(database_session, user_id=current_user.id, project_id=project_id, action="created", resource_type="requirement", resource_id=requirement.id, description=f"Created requirement '{requirement.requirement_key}'")
    database_session.commit()
    database_session.refresh(requirement)
    return requirement


@router.get("/projects/{project_id}/requirements", response_model=list[RequirementRead])
def list_requirements(project_id: uuid.UUID, current_user: CurrentUser, database_session: DatabaseSession, include_deprecated: bool = False) -> list[Requirement]:
    get_accessible_project(database_session, project_id, current_user, VIEW_PROJECT_ROLES)
    query = select(Requirement).where(Requirement.project_id == project_id)
    if not include_deprecated:
        query = query.where(Requirement.status != "deprecated")
    return list(database_session.scalars(query.order_by(Requirement.requirement_key)))


@router.get("/projects/{project_id}/requirements/traceability", response_model=RequirementTraceabilityResponse)
def get_traceability_matrix(
    project_id: uuid.UUID,
    current_user: CurrentUser,
    database_session: DatabaseSession,
    include_deprecated: bool = False,
    status_filter: str | None = Query(default=None, alias="status"),
    priority: str | None = None,
    category: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict:
    get_accessible_project(database_session, project_id, current_user, VIEW_PROJECT_ROLES)
    return build_traceability_matrix(database_session, project_id, include_deprecated=include_deprecated, status=status_filter, priority=priority, category=category, limit=limit, offset=offset)


@router.get("/projects/{project_id}/requirements/traceability.csv")
def export_traceability_matrix_csv(project_id: uuid.UUID, current_user: CurrentUser, database_session: DatabaseSession, include_deprecated: bool = False) -> Response:
    get_accessible_project(database_session, project_id, current_user, VIEW_PROJECT_ROLES)
    matrix = build_traceability_matrix(database_session, project_id, include_deprecated=include_deprecated, limit=500, offset=0)
    items = list(matrix["items"])
    while len(items) < matrix["total"]:
        page = build_traceability_matrix(database_session, project_id, include_deprecated=include_deprecated, limit=500, offset=len(items))
        items.extend(page["items"])
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Requirement key", "Title", "Status", "Priority", "Category", "Coverage", "Linked tests", "Passing tests", "Not passing tests", "Unresolved issues"])
    for row in items:
        writer.writerow([row["requirement_key"], row["title"], row["status"], row["priority"], row["category"], row["coverage_status"], row["linked_test_case_count"], row["passing_test_case_count"], row["not_passing_test_case_count"], row["unresolved_issue_count"]])
    return Response(content=output.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="verigate-rtm-{project_id}.csv"'})


@router.get("/requirements/{requirement_id}", response_model=RequirementRead)
def read_requirement(requirement_id: uuid.UUID, current_user: CurrentUser, database_session: DatabaseSession) -> Requirement:
    return get_owned_requirement(requirement_id, current_user, database_session)


@router.patch("/requirements/{requirement_id}", response_model=RequirementRead)
def update_requirement(requirement_id: uuid.UUID, payload: RequirementUpdate, current_user: CurrentUser, database_session: DatabaseSession) -> Requirement:
    requirement = get_owned_requirement(requirement_id, current_user, database_session, MANAGE_TEST_ASSET_ROLES)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(requirement, field, value)
    try:
        database_session.flush()
    except IntegrityError as exc:
        database_session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Requirement key already exists in this project") from exc
    action = "deprecated" if updates.get("status") == "deprecated" else "updated"
    record_audit_event(database_session, user_id=current_user.id, project_id=requirement.project_id, action=action, resource_type="requirement", resource_id=requirement.id, description=f"{action.capitalize()} requirement '{requirement.requirement_key}'")
    database_session.commit()
    database_session.refresh(requirement)
    return requirement


def _validate_test_case_link(requirement: Requirement, test_case_id: uuid.UUID, current_user: CurrentUser, database_session: Session):
    test_case = get_owned_test_case(test_case_id, current_user.id, database_session, MANAGE_TEST_ASSET_ROLES)
    if test_case.test_suite.project_id != requirement.project_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Test case must belong to the same project as the requirement")
    return test_case


def _validate_issue_link(requirement: Requirement, issue_id: uuid.UUID, current_user: CurrentUser, database_session: Session):
    issue = get_owned_issue(issue_id, current_user.id, database_session)
    get_accessible_project(database_session, requirement.project_id, current_user, MANAGE_TEST_ASSET_ROLES)
    if issue.project_id != requirement.project_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Issue must belong to the same project as the requirement")
    return issue


@router.post("/requirements/{requirement_id}/test-cases/{test_case_id}", response_model=RequirementRead)
def link_test_case(requirement_id: uuid.UUID, test_case_id: uuid.UUID, current_user: CurrentUser, database_session: DatabaseSession) -> Requirement:
    requirement = get_owned_requirement(requirement_id, current_user, database_session, MANAGE_TEST_ASSET_ROLES, with_links=True)
    test_case = _validate_test_case_link(requirement, test_case_id, current_user, database_session)
    if any(item.id == test_case.id for item in requirement.test_cases):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Test case is already linked to this requirement")
    requirement.test_cases.append(test_case)
    record_audit_event(database_session, user_id=current_user.id, project_id=requirement.project_id, action="linked", resource_type="requirement_test_case", resource_id=requirement.id, description=f"Linked a test case to requirement '{requirement.requirement_key}'")
    database_session.commit()
    database_session.refresh(requirement)
    return requirement


@router.delete("/requirements/{requirement_id}/test-cases/{test_case_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_test_case(requirement_id: uuid.UUID, test_case_id: uuid.UUID, current_user: CurrentUser, database_session: DatabaseSession) -> Response:
    requirement = get_owned_requirement(requirement_id, current_user, database_session, MANAGE_TEST_ASSET_ROLES, with_links=True)
    test_case = _validate_test_case_link(requirement, test_case_id, current_user, database_session)
    if not any(item.id == test_case.id for item in requirement.test_cases):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test case link not found")
    requirement.test_cases.remove(test_case)
    record_audit_event(database_session, user_id=current_user.id, project_id=requirement.project_id, action="unlinked", resource_type="requirement_test_case", resource_id=requirement.id, description=f"Unlinked a test case from requirement '{requirement.requirement_key}'")
    database_session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/requirements/{requirement_id}/issues/{issue_id}", response_model=RequirementRead)
def link_issue(requirement_id: uuid.UUID, issue_id: uuid.UUID, current_user: CurrentUser, database_session: DatabaseSession) -> Requirement:
    requirement = get_owned_requirement(requirement_id, current_user, database_session, MANAGE_TEST_ASSET_ROLES, with_links=True)
    issue = _validate_issue_link(requirement, issue_id, current_user, database_session)
    if any(item.id == issue.id for item in requirement.issues):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Issue is already linked to this requirement")
    requirement.issues.append(issue)
    record_audit_event(database_session, user_id=current_user.id, project_id=requirement.project_id, action="linked", resource_type="requirement_issue", resource_id=requirement.id, description=f"Linked an issue to requirement '{requirement.requirement_key}'")
    database_session.commit()
    database_session.refresh(requirement)
    return requirement


@router.delete("/requirements/{requirement_id}/issues/{issue_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_issue(requirement_id: uuid.UUID, issue_id: uuid.UUID, current_user: CurrentUser, database_session: DatabaseSession) -> Response:
    requirement = get_owned_requirement(requirement_id, current_user, database_session, MANAGE_TEST_ASSET_ROLES, with_links=True)
    issue = _validate_issue_link(requirement, issue_id, current_user, database_session)
    if not any(item.id == issue.id for item in requirement.issues):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue link not found")
    requirement.issues.remove(issue)
    record_audit_event(database_session, user_id=current_user.id, project_id=requirement.project_id, action="unlinked", resource_type="requirement_issue", resource_id=requirement.id, description=f"Unlinked an issue from requirement '{requirement.requirement_key}'")
    database_session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
