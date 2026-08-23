from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, File, UploadFile, status

from app.api.dependencies import CurrentUser, SessionDependency
from app.models.chat_message import ChatMessage
from app.schemas.chat import (
    ChatMessageCreate,
    ChatMessageResponse,
    ChatResponse,
    ChatThreadResponse,
    RequirementDocResponse,
    DeleteChatResponse,
    RemoveUploadRequest,
    UploadResponse,
)
from app.services.agent_pipeline import run_project_agent_pipeline
from app.services.chat import ChatService, extract_upload_to_requirement_doc
from app.services.realtime import realtime_manager

router = APIRouter(prefix="/projects/{project_id}/chat", tags=["Chat"])


@router.get("", response_model=ChatThreadResponse)
async def get_chat(
    project_id: UUID,
    user: CurrentUser,
    session: SessionDependency,
) -> ChatThreadResponse:
    chat, uploads = await ChatService(session).get_thread(user.id, project_id)
    return ChatThreadResponse(
        chat=ChatResponse.model_validate(chat),
        messages=[ChatMessageResponse.model_validate(message) for message in chat.messages],
        uploads=[RequirementDocResponse.model_validate(upload) for upload in uploads],
    )


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload(
    project_id: UUID,
    background_tasks: BackgroundTasks,
    user: CurrentUser,
    session: SessionDependency,
    file: UploadFile = File(...),
) -> UploadResponse:
    data = await file.read()
    chat, file_path = await ChatService(session).upload_file(
        user.id,
        project_id,
        file.filename or "upload",
        data,
        file.content_type,
    )
    background_tasks.add_task(
        extract_upload_to_requirement_doc,
        project_id,
        file_path,
        file.filename or "upload",
        data,
    )
    await realtime_manager.broadcast_project(project_id, "upload.accepted", {"project_id": str(project_id), "chat_id": str(chat.id), "file_path": file_path})
    await realtime_manager.broadcast_user(user.id, "upload.accepted", {"project_id": str(project_id), "chat_id": str(chat.id), "file_path": file_path})
    return UploadResponse(chat_id=chat.id, file_path=file_path)


@router.post("/message", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
async def message(
    project_id: UUID,
    payload: ChatMessageCreate,
    background_tasks: BackgroundTasks,
    user: CurrentUser,
    session: SessionDependency,
) -> ChatMessage:
    service = ChatService(session)
    chat_message = await service.add_message(user.id, project_id, payload)
    run, created = await service.create_agent_run(user.id, project_id)
    event_payload = {"project_id": str(project_id), "message_id": str(chat_message.id), "run_id": str(run.id), "created_run": created}
    await realtime_manager.broadcast_project(project_id, "chat.message", event_payload)
    await realtime_manager.broadcast_user(user.id, "chat.message", event_payload)
    if created:
        await realtime_manager.broadcast_project(project_id, "run.queued", {"project_id": str(project_id), "run_id": str(run.id), "status": run.status.value})
        await realtime_manager.broadcast_user(user.id, "run.queued", {"project_id": str(project_id), "run_id": str(run.id), "status": run.status.value})
        background_tasks.add_task(run_project_agent_pipeline, run.id)
    return chat_message


@router.delete("/upload/remove", response_model=DeleteChatResponse)
async def remove_upload(
    project_id: UUID,
    payload: RemoveUploadRequest,
    user: CurrentUser,
    session: SessionDependency,
) -> DeleteChatResponse:
    await ChatService(session).remove_upload(user.id, project_id, payload.file_path)
    return DeleteChatResponse(message="Upload removed")


@router.delete("/delete", response_model=DeleteChatResponse)
async def delete_chat(
    project_id: UUID,
    user: CurrentUser,
    session: SessionDependency,
) -> DeleteChatResponse:
    await ChatService(session).delete_chat(user.id, project_id)
    return DeleteChatResponse(message="Chat deleted")
