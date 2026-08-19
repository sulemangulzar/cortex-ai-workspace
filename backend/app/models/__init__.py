"""SQLAlchemy model registry.

Importing this package registers every model with ``Base.metadata``.
"""

from app.models.agent_step import AgentStep
from app.models.build_request import BuildRequest
from app.models.chat import Chat
from app.models.chat_message import ChatMessage
from app.models.project import Project
from app.models.project_source import ProjectSource
from app.models.refresh_token import RefreshToken
from app.models.engineering_run import EngineeringRun
from app.models.project_versions import ProjectVersion
from app.models.user import User

__all__ = [
    "AgentStep",
    "BuildRequest",
    "Chat",
    "ChatMessage",
    "Project",
    "ProjectSource",
    "ProjectVersion",
    "EngineeringRun",
    "RefreshToken",
    "User",
]
