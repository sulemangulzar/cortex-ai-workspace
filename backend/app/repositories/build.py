from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.agent_task import AgentTask
from app.models.project import Project
from app.models.run import Run


class BuildRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def project_belongs_to_user(self, project_id: UUID, user_id: UUID) -> bool:
        return (await self.session.scalar(select(Project.id).where(Project.id == project_id, Project.user_id == user_id))) is not None

    def add_run(self, run: Run) -> Run:
        self.session.add(run)
        return run

    def add_task(self, task: AgentTask) -> AgentTask:
        self.session.add(task)
        return task

    async def get_run(self, run_id: UUID, project_id: UUID, user_id: UUID) -> Run | None:
        return await self.session.scalar(
            select(Run)
            .options(selectinload(Run.agent_tasks), selectinload(Run.features), selectinload(Run.review_findings))
            .join(Project)
            .where(Run.id == run_id, Run.project_id == project_id, Project.user_id == user_id)
        )

    async def list_runs(self, project_id: UUID, user_id: UUID) -> list[Run]:
        result = await self.session.scalars(
            select(Run)
            .options(selectinload(Run.agent_tasks), selectinload(Run.features), selectinload(Run.review_findings))
            .join(Project)
            .where(Run.project_id == project_id, Project.user_id == user_id)
            .order_by(Run.started_at.desc().nullslast(), Run.id.desc())
        )
        return list(result)
