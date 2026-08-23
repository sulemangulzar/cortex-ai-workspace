from __future__ import annotations

import re
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import AsyncSessionFactory
from app.core.exceptions import NotFoundError, PayloadTooLargeError, ServiceError
from app.models.chat import Chat
from app.models.chat_message import ChatMessage
from app.models.enums import ChatMessageRole
from app.models.project import Project
from app.models.enums import RunStatus
from app.models.requirement_doc import RequirementDoc
from app.models.run import Run
from app.schemas.chat import ChatMessageCreate
from app.services.agent_pipeline import AgentPipelineService
from app.services.document_extractor import extract_text_from_bytes
from app.services.realtime import realtime_manager
from app.services.storage import StorageService


class EmptyDocumentError(ServiceError):
    status_code = 422
    detail = "Uploaded document did not contain extractable text"


SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx"}


def safe_filename(filename: str) -> str:
    name = Path(filename).name.strip() or "upload"
    return SAFE_FILENAME_RE.sub("-", name).strip(".-") or "upload"


class ChatService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def ensure_chat(self, user_id: UUID, project_id: UUID) -> Chat:
        await self._check_project(user_id, project_id)
        chat = await self.session.scalar(select(Chat).where(Chat.project_id == project_id))
        if chat is not None:
            return chat
        chat = Chat(project_id=project_id)
        self.session.add(chat)
        await self.session.commit()
        await self.session.refresh(chat)
        return chat

    async def get_thread(self, user_id: UUID, project_id: UUID) -> tuple[Chat, list[RequirementDoc]]:
        chat = await self.ensure_chat(user_id, project_id)
        chat = await self.session.scalar(select(Chat).options(selectinload(Chat.messages)).where(Chat.id == chat.id))
        uploads = list(await self.session.scalars(select(RequirementDoc).where(RequirementDoc.project_id == project_id).order_by(RequirementDoc.uploaded_at.desc())))
        if chat is None:
            raise NotFoundError("Chat not found")
        return chat, uploads

    async def add_message(self, user_id: UUID, project_id: UUID, payload: ChatMessageCreate) -> ChatMessage:
        chat = await self.ensure_chat(user_id, project_id)
        message = ChatMessage(chat_id=chat.id, role=ChatMessageRole.user, content=payload.content.strip())
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def create_agent_run(self, user_id: UUID, project_id: UUID) -> tuple[Run, bool]:
        await self._check_project(user_id, project_id)
        existing = await self.session.scalar(
            select(Run)
            .where(Run.project_id == project_id, Run.status.in_([RunStatus.pending, RunStatus.running]))
            .order_by(Run.started_at.desc().nullsfirst())
        )
        if existing is not None:
            return existing, False
        return await AgentPipelineService(self.session).create_run(project_id), True

    async def upload_file(self, user_id: UUID, project_id: UUID, filename: str, data: bytes, content_type: str | None) -> tuple[Chat, str]:
        if len(data) > settings.MAX_UPLOAD_SIZE_BYTES:
            raise PayloadTooLargeError()
        cleaned_name = safe_filename(filename)
        extension = Path(cleaned_name).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise ServiceError("Only .pdf, .txt, and .docx uploads are supported")
        chat = await self.ensure_chat(user_id, project_id)
        object_key = f"{user_id}/{project_id}/{chat.id}/{cleaned_name}"
        await StorageService().upload_bytes(object_key, data, content_type)
        return chat, object_key

    async def remove_upload(self, user_id: UUID, project_id: UUID, file_path: str) -> None:
        await self._check_project(user_id, project_id)
        expected_prefix = f"{user_id}/{project_id}/"
        if not file_path.startswith(expected_prefix):
            raise NotFoundError("Upload not found")
        await StorageService().delete_object(file_path)
        await self.session.execute(delete(RequirementDoc).where(RequirementDoc.project_id == project_id, RequirementDoc.file_path == file_path))
        await self.session.commit()

    async def delete_chat(self, user_id: UUID, project_id: UUID) -> None:
        await self._check_project(user_id, project_id)
        chat = await self.session.scalar(select(Chat).options(selectinload(Chat.messages)).where(Chat.project_id == project_id))
        if chat is None:
            raise NotFoundError("Chat not found")
        await self.session.delete(chat)
        await self.session.commit()

    async def _check_project(self, user_id: UUID, project_id: UUID) -> None:
        exists = await self.session.scalar(select(Project.id).where(Project.id == project_id, Project.user_id == user_id))
        if exists is None:
            raise NotFoundError("Project not found")


async def extract_upload_to_requirement_doc(project_id: UUID, file_path: str, filename: str, data: bytes) -> None:
    if AsyncSessionFactory is None:
        return
    async with AsyncSessionFactory() as session:
        try:
            raw_text = extract_text_from_bytes(filename, data)
            if not raw_text:
                raise EmptyDocumentError()
            existing = await session.scalar(select(RequirementDoc).where(RequirementDoc.project_id == project_id, RequirementDoc.file_path == file_path))
            if existing is None:
                session.add(RequirementDoc(project_id=project_id, file_path=file_path, raw_text=raw_text))
            else:
                existing.raw_text = raw_text
            await session.commit()
            owner_id = await session.scalar(select(Project.user_id).where(Project.id == project_id))
            payload = {"project_id": str(project_id), "file_path": file_path}
            await realtime_manager.broadcast_project(project_id, "upload.extracted", payload)
            if owner_id is not None:
                await realtime_manager.broadcast_user(owner_id, "upload.extracted", payload)
        except Exception:
            await session.rollback()
            raise
