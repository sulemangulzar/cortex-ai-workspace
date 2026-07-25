from datetime import datetime, timezone
from uuid import UUID

import jwt
from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import CurrentUser, SessionDependency
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_hash,
    hash_token,
    verify_hash,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    MessageResponse,
    SignupRequest,
    UserResponse,
    UserUpdateRequest,
)

router = APIRouter(prefix="/auth/v1", tags=["Authentication"])
REFRESH_COOKIE_NAME = "refresh_token"


def set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/auth/v1",
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/auth/v1",
    )


async def create_session_tokens(
    session: SessionDependency, user: User
) -> tuple[str, str]:
    access_token = create_access_token(user)
    refresh_token, expires_at = create_refresh_token(user)
    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            expires_at=expires_at,
        )
    )
    await session.flush()
    return access_token, refresh_token


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    payload: SignupRequest,
    response: Response,
    session: SessionDependency,
) -> AuthResponse:
    user = User(
        email=str(payload.email),
        username=payload.username,
        hashed_password=get_hash(payload.password),
        first_name=payload.first_name,
        last_name=payload.last_name,
    )
    session.add(user)

    try:
        await session.flush()
        access_token, refresh_token = await create_session_tokens(session, user)
        await session.commit()
        await session.refresh(user)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email or username already exists",
        ) from None

    set_refresh_cookie(response, refresh_token)
    return AuthResponse(access_token=access_token, user=UserResponse.model_validate(user))


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    session: SessionDependency,
) -> AuthResponse:
    user = await session.scalar(
        select(User).where(func.lower(User.email) == str(payload.email).lower())
    )
    if user is None or not verify_hash(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    user.last_login_at = datetime.now(timezone.utc)
    access_token, refresh_token = await create_session_tokens(session, user)
    await session.commit()
    await session.refresh(user)

    set_refresh_cookie(response, refresh_token)
    return AuthResponse(access_token=access_token, user=UserResponse.model_validate(user))


@router.post("/refresh", response_model=AuthResponse)
async def refresh_access_token(
    request: Request,
    response: Response,
    session: SessionDependency,
) -> AuthResponse:
    token = request.cookies.get(REFRESH_COOKIE_NAME)
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
    )
    if token is None:
        raise unauthorized

    try:
        payload = decode_token(token, "refresh")
        user_id = UUID(payload["sub"])
        token_version = int(payload["ver"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        clear_refresh_cookie(response)
        raise unauthorized from None

    stored_token = await session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(token))
    )
    user = await session.get(User, user_id)
    if (
        stored_token is None
        or stored_token.user_id != user_id
        or stored_token.expires_at <= datetime.now(timezone.utc)
        or user is None
        or not user.is_active
        or user.token_version != token_version
    ):
        clear_refresh_cookie(response)
        raise unauthorized

    # Rotate refresh tokens so a captured token cannot be reused indefinitely.
    await session.delete(stored_token)
    access_token, new_refresh_token = await create_session_tokens(session, user)
    await session.commit()
    await session.refresh(user)

    set_refresh_cookie(response, new_refresh_token)
    return AuthResponse(access_token=access_token, user=UserResponse.model_validate(user))


@router.get("/me", response_model=UserResponse)
async def current_user(user: CurrentUser) -> User:
    return user


@router.patch("/me", response_model=UserResponse)
async def update_user(
    payload: UserUpdateRequest,
    user: CurrentUser,
    session: SessionDependency,
) -> User:
    updates = payload.model_dump(exclude_unset=True)
    if "email" in updates and updates["email"] is not None:
        updates["email"] = str(updates["email"])

    for field, value in updates.items():
        setattr(user, field, value)

    try:
        await session.commit()
        await session.refresh(user)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That email or username is already in use",
        ) from None
    return user


@router.delete("/me", response_model=MessageResponse)
async def delete_user(
    response: Response,
    user: CurrentUser,
    session: SessionDependency,
) -> MessageResponse:
    await session.execute(
        delete(RefreshToken).where(RefreshToken.user_id == user.id)
    )
    await session.delete(user)
    await session.commit()
    clear_refresh_cookie(response)
    return MessageResponse(message="Account deleted")


@router.post("/logout", response_model=MessageResponse)
async def logout(
    response: Response,
    user: CurrentUser,
    session: SessionDependency,
) -> MessageResponse:
    await session.execute(
        delete(RefreshToken).where(RefreshToken.user_id == user.id)
    )
    user.token_version += 1
    await session.commit()
    clear_refresh_cookie(response)
    return MessageResponse(message="Logged out from all sessions")
