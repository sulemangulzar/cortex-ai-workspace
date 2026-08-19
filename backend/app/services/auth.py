from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

import jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AuthenticationError,
    ConflictError,
    InactiveAccountError,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_hash,
    hash_token,
    verify_hash,
)
from app.models.user import User
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository
from app.schemas.auth import LoginRequest, SignupRequest


@dataclass(slots=True)
class AuthSession:
    user: User
    access_token: str
    refresh_token: str


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)

    async def signup(self, payload: SignupRequest) -> User:
        user = User(
            email=str(payload.email),
            username=payload.username,
            hashed_password=get_hash(payload.password),
            password_changed_at=datetime.now(timezone.utc),
            first_name=payload.first_name,
            last_name=payload.last_name,
        )
        self.users.add(user)
        try:
            await self.session.commit()
            await self.session.refresh(user)
        except IntegrityError:
            await self.session.rollback()
            raise ConflictError(
                "An account with that email or username already exists"
            ) from None
        return user

    async def login(self, payload: LoginRequest) -> AuthSession:
        user = await self.users.get_by_identifier(payload.identifier)
        if user is None or not verify_hash(payload.password, user.hashed_password):
            raise AuthenticationError("Invalid email/username or password")
        if not user.is_active:
            raise InactiveAccountError()

        user.last_login_at = datetime.now(timezone.utc)
        result = await self._create_session(user)
        await self.session.commit()
        await self.session.refresh(user)
        return result

    async def refresh(self, raw_token: str | None) -> AuthSession:
        if raw_token is None:
            raise AuthenticationError("Invalid or expired refresh token")

        try:
            payload = decode_token(raw_token, "refresh")
            user_id = UUID(payload["sub"])
            token_version = int(payload["ver"])
        except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
            raise AuthenticationError("Invalid or expired refresh token") from None

        # Hash the presented token before comparing it with the stored digest.
        stored_token = await self.refresh_tokens.get_by_hash(
            hash_token(raw_token), for_update=True
        )
        user = await self.users.get_by_id(user_id)
        if (
            stored_token is None
            or stored_token.user_id != user_id
            or stored_token.expires_at <= datetime.now(timezone.utc)
            or user is None
            or not user.is_active
            or user.token_version != token_version
        ):
            raise AuthenticationError("Invalid or expired refresh token")

        await self.refresh_tokens.delete(stored_token)
        result = await self._create_session(user)
        await self.session.commit()
        await self.session.refresh(user)
        return result

    async def authenticate_access_token(self, raw_token: str | None) -> User:
        if raw_token is None:
            raise AuthenticationError("Invalid or expired access token")
        try:
            payload = decode_token(raw_token, "access")
            user_id = UUID(payload["sub"])
            token_version = int(payload["ver"])
        except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
            raise AuthenticationError("Invalid or expired access token") from None

        user = await self.users.get_by_id(user_id)
        if user is None or not user.is_active or user.token_version != token_version:
            raise AuthenticationError("Invalid or expired access token")
        return user

    async def logout_all(self, user: User) -> None:
        await self.refresh_tokens.delete_all_for_user(user.id)
        user.token_version += 1
        await self.session.commit()

    async def _create_session(self, user: User) -> AuthSession:
        access_token = create_access_token(user)
        refresh_token, expires_at = create_refresh_token(user)

        # Persist only the digest; the raw token exists only in the HTTP-only cookie.
        self.refresh_tokens.add(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            expires_at=expires_at,
        )
        await self.session.flush()
        return AuthSession(
            user=user,
            access_token=access_token,
            refresh_token=refresh_token,
        )
