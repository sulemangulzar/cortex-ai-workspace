from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ChatMessageRole


class ChatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    created_at: datetime


class ChatMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=50_000)


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chat_id: UUID
    role: ChatMessageRole
    content: str
    created_at: datetime


class RequirementDocResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    file_path: str
    uploaded_at: datetime


class ChatThreadResponse(BaseModel):
    chat: ChatResponse
    messages: list[ChatMessageResponse]
    uploads: list[RequirementDocResponse]


class UploadResponse(BaseModel):
    chat_id: UUID
    file_path: str
    status: str = "uploaded"


class RemoveUploadRequest(BaseModel):
    file_path: str = Field(min_length=1, max_length=1024)


class DeleteChatResponse(BaseModel):
    message: str
