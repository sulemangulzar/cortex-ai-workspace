from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.user import User
from app.services.auth import AuthService

SessionDependency = Annotated[AsyncSession, Depends(get_session)]
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    session: SessionDependency,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
) -> User:
    raw_token = None
    if credentials is not None and credentials.scheme.lower() == "bearer":
        raw_token = credentials.credentials
    return await AuthService(session).authenticate_access_token(raw_token)


CurrentUser = Annotated[User, Depends(get_current_user)]
