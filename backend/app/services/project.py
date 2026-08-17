from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.project import Project
from app.repositories.project import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.projects = ProjectRepository(session)

    async def create(self, user_id: UUID, payload: ProjectCreate) -> Project:
        project = Project(
            user_id=user_id,
            name=payload.name,
            description=payload.description,
        )
        self.projects.add(project)
        await self.session.commit()
        await self.session.refresh(project)
        return project

    async def list(self, user_id: UUID) -> list[Project]:
        return await self.projects.list_for_user(user_id)

    async def get(self, user_id: UUID, project_id: UUID) -> Project:
        project = await self.projects.get_by_id(project_id, user_id)
        if project is None:
            raise NotFoundError("Project not found")
        return project

    async def update(
        self,
        user_id: UUID,
        project_id: UUID,
        payload: ProjectUpdate,
    ) -> Project:
        project = await self.get(user_id, project_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(project, field, value)

        await self.session.commit()
        await self.session.refresh(project)
        return project

    async def delete(self, user_id: UUID, project_id: UUID) -> None:
        project = await self.get(user_id, project_id)
        await self.projects.delete(project)
        await self.session.commit()
