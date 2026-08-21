from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.chat import Chat
from app.models.chat_message import ChatMessage
from app.models.enums import Roles
from app.repositories.chat import ChatRepository
from app.schemas.chat import ChatCreate, MessageCreate


class ChatService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.chats = ChatRepository(session)

    async def create(self, user_id: UUID, project_id: UUID, payload: ChatCreate) -> Chat:
        await self._check_project(project_id, user_id)
        chat = self.chats.add_chat(Chat(project_id=project_id, title=payload.title.strip()))
        await self.session.commit()
        await self.session.refresh(chat)
        return chat

    async def list_for_project(self, user_id: UUID, project_id: UUID) -> list[Chat]:
        await self._check_project(project_id, user_id)
        return await self.chats.list_chats(project_id, user_id)

    async def get(self, user_id: UUID, project_id: UUID, chat_id: UUID) -> Chat:
        chat = await self.chats.get_chat(chat_id, project_id, user_id)
        if chat is None:
            raise NotFoundError("Chat not found")
        return chat

    async def messages(self, user_id: UUID, project_id: UUID, chat_id: UUID) -> list[ChatMessage]:
        await self.get(user_id, project_id, chat_id)
        return await self.chats.list_messages(chat_id, project_id, user_id)

    async def add_message(self, user_id: UUID, project_id: UUID, chat_id: UUID, payload: MessageCreate) -> ChatMessage:
        chat = await self.get(user_id, project_id, chat_id)
        message = self.chats.add_message(ChatMessage(id=uuid4(), chat_id=chat.id, role=Roles.user, content=payload.content.strip()))
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def _check_project(self, project_id: UUID, user_id: UUID) -> None:
        if not await self.chats.project_belongs_to_user(project_id, user_id):
            raise NotFoundError("Project not found")
