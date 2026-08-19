import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.db.session import get_db
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter(prefix="/projects")


def get_owned_project(
    project_id: uuid.UUID,
    owner_id: uuid.UUID,
    database_session: Session,
) -> Project:
    project = database_session.scalar(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == owner_id,
        )
    )
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    project_data: ProjectCreate,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> Project:
    project = Project(
        owner_id=current_user.id,
        name=project_data.name,
        description=project_data.description,
    )
    database_session.add(project)
    database_session.commit()
    database_session.refresh(project)
    return project


@router.get("", response_model=list[ProjectRead])
def list_projects(
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> list[Project]:
    return list(
        database_session.scalars(
            select(Project)
            .where(Project.owner_id == current_user.id)
            .order_by(Project.created_at.desc())
        )
    )


@router.get("/{project_id}", response_model=ProjectRead)
def read_project(
    project_id: uuid.UUID,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> Project:
    return get_owned_project(project_id, current_user.id, database_session)


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: uuid.UUID,
    project_data: ProjectUpdate,
    current_user: CurrentUser,
    database_session: Annotated[Session, Depends(get_db)],
) -> Project:
    project = get_owned_project(project_id, current_user.id, database_session)

    for field, value in project_data.model_dump(exclude_unset=True).items():
        setattr(project, field, value)

    database_session.commit()
    database_session.refresh(project)
    return project
