import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.api.routes.projects import get_owned_project
from app.core.permissions import MANAGE_TEST_ASSET_ROLES, VIEW_PROJECT_ROLES
from app.db.session import get_db
from app.models.test_suite import TestSuite
from app.models.user import User
from app.schemas.test_suite import TestSuiteCreate, TestSuiteRead, TestSuiteUpdate
from app.services.audit_service import record_audit_event

router = APIRouter()


def get_owned_test_suite(
    test_suite_id: uuid.UUID,
    owner_id: uuid.UUID,
    database_session: Session,
    allowed_roles: tuple[str, ...] | None = None,
) -> TestSuite:
    test_suite = database_session.get(TestSuite, test_suite_id)
    if test_suite is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test suite not found",
        )
    user = database_session.get(User, owner_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test suite not found",
        )
    get_owned_project(
        test_suite.project_id,
        owner_id,
        database_session,
        allowed_roles or VIEW_PROJECT_ROLES,
    )
    return test_suite


@router.post(
    "/projects/{project_id}/test-suites",
    response_model=TestSuiteRead,
    status_code=status.HTTP_201_CREATED,
)
def create_test_suite(
    project_id: uuid.UUID,
    test_suite_data: TestSuiteCreate,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> TestSuite:
    project = get_owned_project(
        project_id,
        current_user.id,
        database_session,
        MANAGE_TEST_ASSET_ROLES,
    )
    test_suite = TestSuite(
        project_id=project.id,
        name=test_suite_data.name,
        description=test_suite_data.description,
    )
    database_session.add(test_suite)
    database_session.flush()
    record_audit_event(
        database_session,
        user_id=current_user.id,
        project_id=project.id,
        action="created",
        resource_type="test_suite",
        resource_id=test_suite.id,
        description=f"Created test suite '{test_suite.name}'",
    )
    database_session.commit()
    database_session.refresh(test_suite)
    return test_suite


@router.get(
    "/projects/{project_id}/test-suites",
    response_model=list[TestSuiteRead],
)
def list_test_suites(
    project_id: uuid.UUID,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> list[TestSuite]:
    project = get_owned_project(project_id, current_user.id, database_session)
    return list(
        database_session.scalars(
            select(TestSuite)
            .where(TestSuite.project_id == project.id)
            .order_by(TestSuite.created_at.desc())
        )
    )


@router.get("/test-suites/{test_suite_id}", response_model=TestSuiteRead)
def read_test_suite(
    test_suite_id: uuid.UUID,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> TestSuite:
    return get_owned_test_suite(test_suite_id, current_user.id, database_session)


@router.patch("/test-suites/{test_suite_id}", response_model=TestSuiteRead)
def update_test_suite(
    test_suite_id: uuid.UUID,
    test_suite_data: TestSuiteUpdate,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> TestSuite:
    test_suite = get_owned_test_suite(
        test_suite_id,
        current_user.id,
        database_session,
        MANAGE_TEST_ASSET_ROLES,
    )
    for field, value in test_suite_data.model_dump(exclude_unset=True).items():
        setattr(test_suite, field, value)

    record_audit_event(
        database_session,
        user_id=current_user.id,
        project_id=test_suite.project_id,
        action="updated",
        resource_type="test_suite",
        resource_id=test_suite.id,
        description=f"Updated test suite '{test_suite.name}'",
    )
    database_session.commit()
    database_session.refresh(test_suite)
    return test_suite


@router.delete(
    "/test-suites/{test_suite_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_test_suite(
    test_suite_id: uuid.UUID,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> Response:
    test_suite = get_owned_test_suite(
        test_suite_id,
        current_user.id,
        database_session,
        MANAGE_TEST_ASSET_ROLES,
    )
    record_audit_event(
        database_session,
        user_id=current_user.id,
        project_id=test_suite.project_id,
        action="deleted",
        resource_type="test_suite",
        resource_id=test_suite.id,
        description=f"Deleted test suite '{test_suite.name}'",
    )
    database_session.delete(test_suite)
    database_session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
