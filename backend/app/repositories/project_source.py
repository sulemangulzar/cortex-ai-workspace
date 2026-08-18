from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.project_source import ProjectSource


class ProjectSourceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def add(self, source: ProjectSource) -> ProjectSource:
        self.session.add(source)
        return source

    async def get_by_id(
        self,
        source_id: UUID,
        project_id: UUID,
        user_id: UUID,
    ) -> ProjectSource | None:
        return await self.session.scalar(
            select(ProjectSource)
            .join(Project, Project.id == ProjectSource.project_id)
            .where(
                ProjectSource.id == source_id,
                ProjectSource.project_id == project_id,
                Project.user_id == user_id,
            )
        )

    async def list_for_project(
        self, project_id: UUID, user_id: UUID
    ) -> list[ProjectSource]:
        result = await self.session.scalars(
            select(ProjectSource)
            .join(Project, Project.id == ProjectSource.project_id)
            .where(
                ProjectSource.project_id == project_id,
                Project.user_id == user_id,
            )
            .order_by(ProjectSource.created_at.desc())
        )
        return list(result)

    async def project_belongs_to_user(
        self, project_id: UUID, user_id: UUID
    ) -> bool:
        return (
            await self.session.scalar(
                select(Project.id).where(
                    Project.id == project_id,
                    Project.user_id == user_id,
                )
            )
            is not None
        )

    async def delete(self, source: ProjectSource) -> None:
        await self.session.delete(source)
