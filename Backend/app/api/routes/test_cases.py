import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.api.routes.test_suites import get_owned_test_suite
from app.db.session import get_db
from app.models.project import Project
from app.models.test_case import TestCase
from app.models.test_suite import TestSuite
from app.schemas.test_case import TestCaseCreate, TestCaseRead, TestCaseUpdate

router = APIRouter()


def get_owned_test_case(
    test_case_id: uuid.UUID,
    owner_id: uuid.UUID,
    database_session: Session,
) -> TestCase:
    test_case = database_session.scalar(
        select(TestCase)
        .join(TestSuite)
        .join(Project)
        .where(
            TestCase.id == test_case_id,
            Project.owner_id == owner_id,
        )
    )
    if test_case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test case not found",
        )
    return test_case


@router.post(
    "/test-suites/{test_suite_id}/test-cases",
    response_model=TestCaseRead,
    status_code=status.HTTP_201_CREATED,
)
def create_test_case(
    test_suite_id: uuid.UUID,
    test_case_data: TestCaseCreate,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> TestCase:
    test_suite = get_owned_test_suite(
        test_suite_id,
        current_user.id,
        database_session,
    )
    test_case = TestCase(
        test_suite_id=test_suite.id,
        **test_case_data.model_dump(),
    )
    database_session.add(test_case)
    database_session.commit()
    database_session.refresh(test_case)
    return test_case


@router.get(
    "/test-suites/{test_suite_id}/test-cases",
    response_model=list[TestCaseRead],
)
def list_test_cases(
    test_suite_id: uuid.UUID,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> list[TestCase]:
    test_suite = get_owned_test_suite(
        test_suite_id,
        current_user.id,
        database_session,
    )
    return list(
        database_session.scalars(
            select(TestCase)
            .where(TestCase.test_suite_id == test_suite.id)
            .order_by(TestCase.created_at.desc())
        )
    )


@router.get("/test-cases/{test_case_id}", response_model=TestCaseRead)
def read_test_case(
    test_case_id: uuid.UUID,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> TestCase:
    return get_owned_test_case(test_case_id, current_user.id, database_session)


@router.patch("/test-cases/{test_case_id}", response_model=TestCaseRead)
def update_test_case(
    test_case_id: uuid.UUID,
    test_case_data: TestCaseUpdate,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> TestCase:
    test_case = get_owned_test_case(test_case_id, current_user.id, database_session)
    for field, value in test_case_data.model_dump(exclude_unset=True).items():
        setattr(test_case, field, value)

    database_session.commit()
    database_session.refresh(test_case)
    return test_case
