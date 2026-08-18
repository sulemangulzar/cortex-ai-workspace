from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    PayloadTooLargeError,
    StorageError,
)
from app.core.supabase import s3_config
from app.models.enums import ProjectSourceStatus, SourceType
from app.models.project_source import ProjectSource
from app.repositories.project_source import ProjectSourceRepository
from app.schemas.project_source import ProjectSourceCreate, ProjectSourceUpdate


class ProjectSourceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.sources = ProjectSourceRepository(session)

    async def create(
        self,
        user_id: UUID,
        project_id: UUID,
        payload: ProjectSourceCreate,
    ) -> ProjectSource:
        await self._ensure_project_access(project_id, user_id)
        source = ProjectSource(
            project_id=project_id,
            source_type=payload.source_type,
            bucket=payload.bucket,
            object_path=payload.object_path,
            original_filename=payload.original_filename,
            size_bytes=payload.size_bytes,
            status=payload.status,
        )
        self.sources.add(source)
        try:
            await self.session.commit()
            await self.session.refresh(source)
        except IntegrityError:
            await self.session.rollback()
            raise ConflictError("That object path is already registered") from None
        return source

    async def upload(
        self,
        user_id: UUID,
        project_id: UUID,
        file: UploadFile,
        source_type: SourceType,
    ) -> ProjectSource:
        await self._ensure_project_access(project_id, user_id)

        filename = Path(file.filename or "upload").name
        if not filename or filename in {".", ".."}:
            raise StorageError("Uploaded file must have a valid filename")

        file.file.seek(0, 2)
        size_bytes = file.file.tell()
        file.file.seek(0)
        if size_bytes > settings.MAX_UPLOAD_SIZE_BYTES:
            raise PayloadTooLargeError(
                f"File exceeds the {settings.MAX_UPLOAD_SIZE_BYTES} byte limit"
            )

        bucket = settings.BUCKET_NAME
        if not bucket:
            raise StorageError("Object storage bucket is not configured")

        source_id = uuid4()
        object_path = f"{user_id}/{project_id}/{source_id}/{filename}"
        source = ProjectSource(
            id=source_id,
            project_id=project_id,
            source_type=source_type,
            bucket=bucket,
            object_path=object_path,
            original_filename=filename,
            size_bytes=size_bytes,
            status=ProjectSourceStatus.uploading,
        )
        self.sources.add(source)
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(source)

        try:
            await s3_config.upload_fileobj(
                file.file,
                bucket,
                object_path,
                file.content_type,
            )
        except Exception as exc:
            source.status = ProjectSourceStatus.failed
            await self.session.commit()
            raise StorageError("Could not upload the file to object storage") from exc

        source.status = ProjectSourceStatus.uploaded
        await self.session.commit()
        await self.session.refresh(source)
        return source

    async def list(self, user_id: UUID, project_id: UUID) -> list[ProjectSource]:
        await self._ensure_project_access(project_id, user_id)
        return await self.sources.list_for_project(project_id, user_id)

    async def get(
        self, user_id: UUID, project_id: UUID, source_id: UUID
    ) -> ProjectSource:
        source = await self.sources.get_by_id(source_id, project_id, user_id)
        if source is None:
            raise NotFoundError("Project source not found")
        return source

    async def update(
        self,
        user_id: UUID,
        project_id: UUID,
        source_id: UUID,
        payload: ProjectSourceUpdate,
    ) -> ProjectSource:
        source = await self.get(user_id, project_id, source_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(source, field, value)
        await self.session.commit()
        await self.session.refresh(source)
        return source

    async def delete(self, user_id: UUID, project_id: UUID, source_id: UUID) -> None:
        source = await self.get(user_id, project_id, source_id)
        if source.status == ProjectSourceStatus.uploaded:
            try:
                await s3_config.delete_object(source.bucket, source.object_path)
            except Exception as exc:
                raise StorageError(
                    "Could not remove the file from object storage"
                ) from exc
        await self.sources.delete(source)
        await self.session.commit()

    async def _ensure_project_access(self, project_id: UUID, user_id: UUID) -> None:
        if not await self.sources.project_belongs_to_user(project_id, user_id):
            raise NotFoundError("Project not found")
