from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, status

from app.api.dependencies import CurrentUser, SessionDependency
from app.models.engineering_run import EngineeringRun
from app.schemas.build import BuildCreate, BuildRequestResponse, BuildResponse, EngineeringRunResponse
from app.services.build import BuildService
from app.services.crew import run_engineering_run

router = APIRouter(prefix="/projects/{project_id}", tags=["Build"])


@router.post("/builds", response_model=BuildResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_build(
    project_id: UUID,
    payload: BuildCreate,
    background_tasks: BackgroundTasks,
    user: CurrentUser,
    session: SessionDependency,
) -> BuildResponse:
    request, run = await BuildService(session).create(user.id, project_id, payload)
    background_tasks.add_task(run_engineering_run, run.id)
    return BuildResponse(
        request=BuildRequestResponse.model_validate(request),
        run=EngineeringRunResponse.model_validate(run),
    )


@router.get("/builds", response_model=list[EngineeringRunResponse])
async def list_builds(project_id: UUID, user: CurrentUser, session: SessionDependency) -> list[EngineeringRun]:
    return await BuildService(session).list_for_project(user.id, project_id)


@router.get("/builds/{run_id}", response_model=EngineeringRunResponse)
async def get_build(project_id: UUID, run_id: UUID, user: CurrentUser, session: SessionDependency) -> EngineeringRun:
    return await BuildService(session).get(user.id, project_id, run_id)
