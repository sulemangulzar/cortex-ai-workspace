from uuid import UUID

from fastapi import APIRouter, Response, status

from app.api.dependencies import CurrentUser, SessionDependency
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.project import ProjectService

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    payload: ProjectCreate,
    user: CurrentUser,
    session: SessionDependency,
) -> Project:
    return await ProjectService(session).create(user.id, payload)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    user: CurrentUser,
    session: SessionDependency,
) -> list[Project]:
    return await ProjectService(session).list(user.id)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    user: CurrentUser,
    session: SessionDependency,
) -> Project:
    return await ProjectService(session).get(user.id, project_id)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
    user: CurrentUser,
    session: SessionDependency,
) -> Project:
    return await ProjectService(session).update(user.id, project_id, payload)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    user: CurrentUser,
    session: SessionDependency,
) -> Response:
    await ProjectService(session).delete(user.id, project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
