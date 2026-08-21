from uuid import UUID

from fastapi import APIRouter, status

from app.api.dependencies import CurrentUser, SessionDependency
from app.models.chat import Chat
from app.models.chat_message import ChatMessage
from app.schemas.chat import ChatCreate, ChatResponse, MessageCreate, MessageResponse
from app.services.chat import ChatService

router = APIRouter(prefix="/projects/{project_id}", tags=["Chat"])


@router.post("/chats", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def create_chat(project_id: UUID, payload: ChatCreate, user: CurrentUser, session: SessionDependency) -> Chat:
    return await ChatService(session).create(user.id, project_id, payload)


@router.get("/chats", response_model=list[ChatResponse])
async def list_chats(project_id: UUID, user: CurrentUser, session: SessionDependency) -> list[Chat]:
    return await ChatService(session).list_for_project(user.id, project_id)


@router.get("/chats/{chat_id}", response_model=ChatResponse)
async def get_chat(project_id: UUID, chat_id: UUID, user: CurrentUser, session: SessionDependency) -> Chat:
    return await ChatService(session).get(user.id, project_id, chat_id)


@router.get("/chats/{chat_id}/messages", response_model=list[MessageResponse])
async def list_messages(project_id: UUID, chat_id: UUID, user: CurrentUser, session: SessionDependency) -> list[ChatMessage]:
    return await ChatService(session).messages(user.id, project_id, chat_id)


@router.post("/chats/{chat_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def add_message(project_id: UUID, chat_id: UUID, payload: MessageCreate, user: CurrentUser, session: SessionDependency) -> ChatMessage:
    return await ChatService(session).add_message(user.id, project_id, chat_id, payload)
