from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.agent_task import AgentTask
from app.models.run import Run
from app.repositories.build import BuildRepository
from app.schemas.build import BuildCreate
from app.services.crew import AGENT_NAMES


class BuildService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.builds = BuildRepository(session)

    async def create(self, user_id: UUID, project_id: UUID, payload: BuildCreate) -> Run:
        await self._check_project(project_id, user_id)
        run = self.builds.add_run(Run(project_id=project_id))
        await self.session.flush()
        for agent_name in AGENT_NAMES:
            self.builds.add_task(
                AgentTask(
                    run_id=run.id,
                    agent_name=agent_name,
                    input=payload.requirement.strip(),
                    revision_cycle=0,
                )
            )
        await self.session.commit()
        return await self.get(user_id, project_id, run.id)

    async def list_for_project(self, user_id: UUID, project_id: UUID) -> list[Run]:
        await self._check_project(project_id, user_id)
        return await self.builds.list_runs(project_id, user_id)

    async def get(self, user_id: UUID, project_id: UUID, run_id: UUID) -> Run:
        run = await self.builds.get_run(run_id, project_id, user_id)
        if run is None:
            raise NotFoundError("Run not found")
        return run

    async def _check_project(self, project_id: UUID, user_id: UUID) -> None:
        if not await self.builds.project_belongs_to_user(project_id, user_id):
            raise NotFoundError("Project not found")
