from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, StorageError
from app.models.project import Project
from app.repositories.project import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.realtime import realtime_manager
from app.services.storage import StorageService


class ProjectService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.projects = ProjectRepository(session)

    async def create(self, user_id: UUID, payload: ProjectCreate) -> Project:
        project = Project(user_id=user_id, name=payload.name)
        self.projects.add(project)
        await self.session.commit()
        await self.session.refresh(project)
        await realtime_manager.broadcast_user(user_id, "project.created", {"project_id": str(project.id), "name": project.name})
        return project

    async def list(self, user_id: UUID) -> list[Project]:
        return await self.projects.list_for_user(user_id)

    async def get(self, user_id: UUID, project_id: UUID) -> Project:
        project = await self.projects.get_by_id(project_id, user_id)
        if project is None:
            raise NotFoundError("Project not found")
        return project

    async def update(self, user_id: UUID, project_id: UUID, payload: ProjectUpdate) -> Project:
        project = await self.get(user_id, project_id)
        if payload.name is not None:
            project.name = payload.name
        await self.session.commit()
        await self.session.refresh(project)
        await realtime_manager.broadcast_user(user_id, "project.updated", {"project_id": str(project.id), "name": project.name})
        await realtime_manager.broadcast_project(project.id, "project.updated", {"project_id": str(project.id), "name": project.name})
        return project

    async def delete(self, user_id: UUID, project_id: UUID) -> None:
        project = await self.get(user_id, project_id)
        try:
            await StorageService().delete_prefix(f"{user_id}/{project_id}/")
        except (RuntimeError, StorageError):
            # Storage can be unavailable in local/dev environments; DB deletion should still proceed.
            pass
        await self.projects.delete(project)
        await self.session.commit()
        payload = {"project_id": str(project_id)}
        await realtime_manager.broadcast_user(user_id, "project.deleted", payload)
        await realtime_manager.broadcast_project(project_id, "project.deleted", payload)
