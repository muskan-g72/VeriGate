import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.dependencies import CurrentUser
from app.api.routes.test_suites import get_owned_test_suite
from app.core.permissions import MANAGE_TEST_ASSET_ROLES, VIEW_PROJECT_ROLES
from app.db.session import get_db
from app.models.scheduled_run import ScheduledRun
from app.schemas.scheduled_run import ScheduledRunCreate, ScheduledRunRead, ScheduledRunUpdate
from app.services.audit_service import record_audit_event
from app.services.scheduled_run_service import execute_scheduled_run

router = APIRouter()
DatabaseSession = Annotated[object, Depends(get_db)]


@router.get("/test-suites/{test_suite_id}/scheduled-runs", response_model=list[ScheduledRunRead])
def list_schedules(test_suite_id: uuid.UUID, current_user: CurrentUser, database_session: DatabaseSession):
    suite = get_owned_test_suite(test_suite_id, current_user.id, database_session, VIEW_PROJECT_ROLES)
    return list(database_session.scalars(select(ScheduledRun).where(ScheduledRun.test_suite_id == suite.id).order_by(ScheduledRun.created_at.desc())))


@router.post("/test-suites/{test_suite_id}/scheduled-runs", response_model=ScheduledRunRead, status_code=status.HTTP_201_CREATED)
def create_schedule(test_suite_id: uuid.UUID, payload: ScheduledRunCreate, current_user: CurrentUser, database_session: DatabaseSession):
    suite = get_owned_test_suite(test_suite_id, current_user.id, database_session, MANAGE_TEST_ASSET_ROLES)
    schedule = ScheduledRun(test_suite_id=suite.id, created_by_id=current_user.id, name=payload.name.strip(), interval_minutes=payload.interval_minutes, enabled=payload.enabled, next_run_at=datetime.now(UTC) + timedelta(minutes=payload.interval_minutes))
    database_session.add(schedule)
    database_session.flush()
    record_audit_event(database_session, user_id=current_user.id, project_id=suite.project_id, action="created", resource_type="scheduled_run", resource_id=schedule.id, description=f"Created scheduled run '{schedule.name}' every {schedule.interval_minutes} minutes")
    database_session.commit(); database_session.refresh(schedule)
    return schedule


@router.patch("/scheduled-runs/{schedule_id}", response_model=ScheduledRunRead)
def update_schedule(schedule_id: uuid.UUID, payload: ScheduledRunUpdate, current_user: CurrentUser, database_session: DatabaseSession):
    schedule = database_session.get(ScheduledRun, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Scheduled run not found")
    suite = get_owned_test_suite(schedule.test_suite_id, current_user.id, database_session, MANAGE_TEST_ASSET_ROLES)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(schedule, field, value.strip() if field == "name" and value else value)
    if payload.interval_minutes is not None or payload.enabled is True:
        schedule.next_run_at = datetime.now(UTC) + timedelta(minutes=schedule.interval_minutes)
    record_audit_event(database_session, user_id=current_user.id, project_id=suite.project_id, action="updated", resource_type="scheduled_run", resource_id=schedule.id, description=f"Updated scheduled run '{schedule.name}'")
    database_session.commit(); database_session.refresh(schedule)
    return schedule


@router.post("/scheduled-runs/{schedule_id}/run-now", response_model=ScheduledRunRead)
async def run_schedule_now(schedule_id: uuid.UUID, current_user: CurrentUser, database_session: DatabaseSession):
    schedule = database_session.get(ScheduledRun, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Scheduled run not found")
    get_owned_test_suite(schedule.test_suite_id, current_user.id, database_session, MANAGE_TEST_ASSET_ROLES)
    await execute_scheduled_run(schedule.id)
    database_session.refresh(schedule)
    return schedule
