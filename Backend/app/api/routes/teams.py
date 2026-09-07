import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.db.session import get_db
from app.models.team import Team
from app.models.team_member import TeamMember
from app.models.user import User
from app.schemas.team import (
    TeamCreate,
    TeamMemberCreate,
    TeamMemberResponse,
    TeamResponse,
    TeamUpdate,
)
from app.services.audit_service import record_audit_event

router = APIRouter(prefix="/teams")


def get_team_or_404(
    team_id: uuid.UUID,
    database_session: Session,
) -> Team:
    team = database_session.get(Team, team_id)
    if team is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )
    return team


def require_team_lead(
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    database_session: Session,
) -> TeamMember:
    membership = database_session.scalar(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
            TeamMember.role == "lead",
        )
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Team lead access required",
        )
    return membership


@router.get("", response_model=list[TeamResponse])
def list_teams(
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> list[Team]:
    return list(
        database_session.scalars(select(Team).order_by(Team.created_at.desc()))
    )


@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
def create_team(
    team_data: TeamCreate,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> Team:
    team = Team(name=team_data.name, description=team_data.description)
    database_session.add(team)
    database_session.flush()
    database_session.add(
        TeamMember(team_id=team.id, user_id=current_user.id, role="lead")
    )
    record_audit_event(
        database_session,
        user_id=current_user.id,
        action="created",
        resource_type="team",
        resource_id=team.id,
        description=f"Created team '{team.name}'",
    )
    database_session.commit()
    database_session.refresh(team)
    return team


@router.get("/{team_id}", response_model=TeamResponse)
def read_team(
    team_id: uuid.UUID,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> Team:
    return get_team_or_404(team_id, database_session)


@router.patch("/{team_id}", response_model=TeamResponse)
def update_team(
    team_id: uuid.UUID,
    team_data: TeamUpdate,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> Team:
    team = get_team_or_404(team_id, database_session)
    require_team_lead(team_id, current_user.id, database_session)
    for field, value in team_data.model_dump(exclude_unset=True).items():
        setattr(team, field, value)
    record_audit_event(
        database_session,
        user_id=current_user.id,
        action="updated",
        resource_type="team",
        resource_id=team.id,
        description=f"Updated team '{team.name}'",
    )
    database_session.commit()
    database_session.refresh(team)
    return team


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_team(
    team_id: uuid.UUID,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> Response:
    team = get_team_or_404(team_id, database_session)
    require_team_lead(team_id, current_user.id, database_session)
    record_audit_event(
        database_session,
        user_id=current_user.id,
        action="deleted",
        resource_type="team",
        resource_id=team.id,
        description=f"Deleted team '{team.name}'",
    )
    database_session.delete(team)
    database_session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{team_id}/members", response_model=list[TeamMemberResponse])
def list_team_members(
    team_id: uuid.UUID,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> list[TeamMember]:
    get_team_or_404(team_id, database_session)
    return list(
        database_session.scalars(
            select(TeamMember)
            .where(TeamMember.team_id == team_id)
            .order_by(TeamMember.joined_at)
        )
    )


@router.post(
    "/{team_id}/members",
    response_model=TeamMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_team_member(
    team_id: uuid.UUID,
    member_data: TeamMemberCreate,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> TeamMember:
    get_team_or_404(team_id, database_session)
    require_team_lead(team_id, current_user.id, database_session)
    if database_session.get(User, member_data.user_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    member = TeamMember(
        team_id=team_id,
        user_id=member_data.user_id,
        role=member_data.role,
    )
    database_session.add(member)
    try:
        record_audit_event(
            database_session,
            user_id=current_user.id,
            action="assigned",
            resource_type="member",
            resource_id=member_data.user_id,
            description=f"Added user to team {team_id}",
        )
        database_session.commit()
    except IntegrityError as error:
        database_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this team",
        ) from error
    database_session.refresh(member)
    return member


@router.delete(
    "/{team_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_team_member(
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> Response:
    get_team_or_404(team_id, database_session)
    require_team_lead(team_id, current_user.id, database_session)
    member = database_session.scalar(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
        )
    )
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team member not found",
        )
    record_audit_event(
        database_session,
        user_id=current_user.id,
        action="deleted",
        resource_type="member",
        resource_id=user_id,
        description=f"Removed user from team {team_id}",
    )
    database_session.delete(member)
    database_session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
