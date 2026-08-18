from uuid import UUID

from fastapi import APIRouter, File, Form, Response, UploadFile, status

from app.api.dependencies import CurrentUser, SessionDependency
from app.models.enums import SourceType
from app.models.project_source import ProjectSource
from app.schemas.project_source import (
    ProjectSourceCreate,
    ProjectSourceResponse,
    ProjectSourceUpdate,
)
from app.services.project_source import ProjectSourceService

router = APIRouter(prefix="/projects/{project_id}/sources", tags=["Project Sources"])


@router.post(
    "/upload",
    response_model=ProjectSourceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_project_source(
    project_id: UUID,
    user: CurrentUser,
    session: SessionDependency,
    file: UploadFile = File(...),
    source_type: SourceType = Form(SourceType.zip),
) -> ProjectSource:
    return await ProjectSourceService(session).upload(
        user.id, project_id, file, source_type
    )


@router.post("", response_model=ProjectSourceResponse, status_code=status.HTTP_201_CREATED)
async def create_project_source(
    project_id: UUID,
    payload: ProjectSourceCreate,
    user: CurrentUser,
    session: SessionDependency,
) -> ProjectSource:
    return await ProjectSourceService(session).create(user.id, project_id, payload)


@router.get("", response_model=list[ProjectSourceResponse])
async def list_project_sources(
    project_id: UUID,
    user: CurrentUser,
    session: SessionDependency,
) -> list[ProjectSource]:
    return await ProjectSourceService(session).list(user.id, project_id)


@router.get("/{source_id}", response_model=ProjectSourceResponse)
async def get_project_source(
    project_id: UUID,
    source_id: UUID,
    user: CurrentUser,
    session: SessionDependency,
) -> ProjectSource:
    return await ProjectSourceService(session).get(user.id, project_id, source_id)


@router.patch("/{source_id}", response_model=ProjectSourceResponse)
async def update_project_source(
    project_id: UUID,
    source_id: UUID,
    payload: ProjectSourceUpdate,
    user: CurrentUser,
    session: SessionDependency,
) -> ProjectSource:
    return await ProjectSourceService(session).update(
        user.id, project_id, source_id, payload
    )


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project_source(
    project_id: UUID,
    source_id: UUID,
    user: CurrentUser,
    session: SessionDependency,
) -> Response:
    await ProjectSourceService(session).delete(user.id, project_id, source_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
