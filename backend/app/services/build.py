from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.build_request import BuildRequest
from app.models.engineering_run import EngineeringRun
from app.repositories.build import BuildRepository
from app.schemas.build import BuildCreate


class BuildService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.builds = BuildRepository(session)

    async def create(self, user_id: UUID, project_id: UUID, payload: BuildCreate) -> tuple[BuildRequest, EngineeringRun]:
        await self._check_project(project_id, user_id)
        request = self.builds.add_request(BuildRequest(project_id=project_id, requirement=payload.requirement.strip()))
        await self.session.flush()
        run = self.builds.add_run(EngineeringRun(build_request_id=request.id, project_id=project_id, requirements_json={"requirement": payload.requirement.strip()}))
        await self.session.commit()
        await self.session.refresh(request)
        await self.session.refresh(run)
        return request, run

    async def list_for_project(self, user_id: UUID, project_id: UUID) -> list[EngineeringRun]:
        await self._check_project(project_id, user_id)
        return await self.builds.list_runs(project_id, user_id)

    async def get(self, user_id: UUID, project_id: UUID, run_id: UUID) -> EngineeringRun:
        run = await self.builds.get_run(run_id, project_id, user_id)
        if run is None:
            raise NotFoundError("Engineering run not found")
        return run

    async def _check_project(self, project_id: UUID, user_id: UUID) -> None:
        if not await self.builds.project_belongs_to_user(project_id, user_id):
            raise NotFoundError("Project not found")
