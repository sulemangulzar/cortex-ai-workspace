from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select

from app.core.database import AsyncSessionFactory
from app.models.project import Project
from app.services.auth import AuthService
from app.services.realtime import realtime_manager

router = APIRouter(tags=["Realtime"])


@router.websocket("/ws")
async def user_socket(websocket: WebSocket, token: str | None = None) -> None:
    user_id = await _authenticate_websocket(websocket, token)
    if user_id is None:
        return
    await realtime_manager.connect(websocket, user_id)
    await websocket.send_json({"event": "connected", "payload": {"scope": "user"}})
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await realtime_manager.disconnect(websocket, user_id)


@router.websocket("/projects/{project_id}/ws")
async def project_socket(websocket: WebSocket, project_id: UUID, token: str | None = None) -> None:
    user_id = await _authenticate_websocket(websocket, token, project_id)
    if user_id is None:
        return
    await realtime_manager.connect(websocket, user_id, project_id)
    await websocket.send_json({"event": "connected", "payload": {"scope": "project", "project_id": str(project_id)}})
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await realtime_manager.disconnect(websocket, user_id, project_id)


async def _authenticate_websocket(websocket: WebSocket, token: str | None, project_id: UUID | None = None) -> UUID | None:
    if AsyncSessionFactory is None or token is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None
    async with AsyncSessionFactory() as session:
        try:
            user = await AuthService(session).authenticate_access_token(token)
            if project_id is not None:
                project_exists = await session.scalar(select(Project.id).where(Project.id == project_id, Project.user_id == user.id))
                if project_exists is None:
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                    return None
            return user.id
        except Exception:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return None
