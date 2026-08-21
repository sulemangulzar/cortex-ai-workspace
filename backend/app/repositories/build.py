from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.build_request import BuildRequest
from app.models.engineering_run import EngineeringRun
from app.models.project import Project


class BuildRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def project_belongs_to_user(self, project_id: UUID, user_id: UUID) -> bool:
        return (await self.session.scalar(select(Project.id).where(Project.id == project_id, Project.user_id == user_id))) is not None

    def add_request(self, request: BuildRequest) -> BuildRequest:
        self.session.add(request)
        return request

    def add_run(self, run: EngineeringRun) -> EngineeringRun:
        self.session.add(run)
        return run

    async def get_run(self, run_id: UUID, project_id: UUID, user_id: UUID) -> EngineeringRun | None:
        return await self.session.scalar(select(EngineeringRun).options(selectinload(EngineeringRun.agent_steps)).join(Project).where(EngineeringRun.id == run_id, EngineeringRun.project_id == project_id, Project.user_id == user_id))

    async def list_runs(self, project_id: UUID, user_id: UUID) -> list[EngineeringRun]:
        result = await self.session.scalars(select(EngineeringRun).options(selectinload(EngineeringRun.agent_steps)).join(Project).where(EngineeringRun.project_id == project_id, Project.user_id == user_id).order_by(EngineeringRun.created_at.desc()))
        return list(result)
