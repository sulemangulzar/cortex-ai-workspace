from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project


class ProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def add(self, project: Project) -> Project:
        self.session.add(project)
        return project

    async def get_by_id(self, project_id: UUID, user_id: UUID) -> Project | None:
        return await self.session.scalar(
            select(Project).where(
                Project.id == project_id,
                Project.user_id == user_id,
            )
        )

    async def list_for_user(self, user_id: UUID) -> list[Project]:
        result = await self.session.scalars(
            select(Project)
            .where(Project.user_id == user_id)
            .order_by(Project.created_at.desc())
        )
        return list(result)

    async def delete(self, project: Project) -> None:
        await self.session.delete(project)
