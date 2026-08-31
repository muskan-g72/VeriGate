import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.api.routes.projects import get_owned_project
from app.db.session import get_db
from app.models.project import Project
from app.models.test_suite import TestSuite
from app.schemas.test_suite import TestSuiteCreate, TestSuiteRead, TestSuiteUpdate

router = APIRouter()


def get_owned_test_suite(
    test_suite_id: uuid.UUID,
    owner_id: uuid.UUID,
    database_session: Session,
) -> TestSuite:
    test_suite = database_session.scalar(
        select(TestSuite)
        .join(Project)
        .where(
            TestSuite.id == test_suite_id,
            Project.owner_id == owner_id,
        )
    )
    if test_suite is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test suite not found",
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
    project = get_owned_project(project_id, current_user.id, database_session)
    test_suite = TestSuite(
        project_id=project.id,
        name=test_suite_data.name,
        description=test_suite_data.description,
    )
    database_session.add(test_suite)
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
    )
    for field, value in test_suite_data.model_dump(exclude_unset=True).items():
        setattr(test_suite, field, value)

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
    test_suite = get_owned_test_suite(test_suite_id, current_user.id, database_session)
    database_session.delete(test_suite)
    database_session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
