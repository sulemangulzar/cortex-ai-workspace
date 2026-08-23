from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any
from uuid import UUID

from fastapi import WebSocket


class RealtimeManager:
    def __init__(self) -> None:
        self._user_connections: dict[UUID, set[WebSocket]] = defaultdict(set)
        self._project_connections: dict[UUID, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: UUID, project_id: UUID | None = None) -> None:
        await websocket.accept()
        async with self._lock:
            self._user_connections[user_id].add(websocket)
            if project_id is not None:
                self._project_connections[project_id].add(websocket)

    async def disconnect(self, websocket: WebSocket, user_id: UUID, project_id: UUID | None = None) -> None:
        async with self._lock:
            self._user_connections[user_id].discard(websocket)
            if not self._user_connections[user_id]:
                self._user_connections.pop(user_id, None)
            if project_id is not None:
                self._project_connections[project_id].discard(websocket)
                if not self._project_connections[project_id]:
                    self._project_connections.pop(project_id, None)

    async def broadcast_user(self, user_id: UUID, event: str, payload: dict[str, Any] | None = None) -> None:
        await self._broadcast(self._user_connections.get(user_id, set()), event, payload)

    async def broadcast_project(self, project_id: UUID, event: str, payload: dict[str, Any] | None = None) -> None:
        await self._broadcast(self._project_connections.get(project_id, set()), event, payload)

    async def _broadcast(self, connections: set[WebSocket], event: str, payload: dict[str, Any] | None) -> None:
        if not connections:
            return
        message = {"event": event, "payload": payload or {}}
        stale: list[WebSocket] = []
        for websocket in list(connections):
            try:
                await websocket.send_json(message)
            except Exception:
                stale.append(websocket)
        if stale:
            async with self._lock:
                for websocket in stale:
                    for sockets in self._user_connections.values():
                        sockets.discard(websocket)
                    for sockets in self._project_connections.values():
                        sockets.discard(websocket)


realtime_manager = RealtimeManager()
