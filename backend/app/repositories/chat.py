from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import Chat
from app.models.chat_message import ChatMessage
from app.models.project import Project


class ChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def project_belongs_to_user(self, project_id: UUID, user_id: UUID) -> bool:
        return (await self.session.scalar(select(Project.id).where(Project.id == project_id, Project.user_id == user_id))) is not None

    def add_chat(self, chat: Chat) -> Chat:
        self.session.add(chat)
        return chat

    async def get_chat(self, chat_id: UUID, project_id: UUID, user_id: UUID) -> Chat | None:
        return await self.session.scalar(select(Chat).join(Project).where(Chat.id == chat_id, Chat.project_id == project_id, Project.user_id == user_id))

    async def list_chats(self, project_id: UUID, user_id: UUID) -> list[Chat]:
        result = await self.session.scalars(select(Chat).join(Project).where(Chat.project_id == project_id, Project.user_id == user_id).order_by(Chat.updated_at.desc()))
        return list(result)

    def add_message(self, message: ChatMessage) -> ChatMessage:
        self.session.add(message)
        return message

    async def list_messages(self, chat_id: UUID, project_id: UUID, user_id: UUID) -> list[ChatMessage]:
        result = await self.session.scalars(select(ChatMessage).join(Chat).join(Project).where(ChatMessage.chat_id == chat_id, Chat.id == chat_id, Chat.project_id == project_id, Project.user_id == user_id).order_by(ChatMessage.created_at.asc()))
        return list(result)
