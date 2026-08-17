from fastapi import APIRouter, Request, Response, status

from app.api.cookies import (
    REFRESH_COOKIE_NAME,
    clear_refresh_cookie,
    set_refresh_cookie,
)
from app.api.dependencies import CurrentUser, SessionDependency
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    MessageResponse,
    SignupRequest,
    UserResponse,
    UserUpdateRequest,
)
from app.services.auth import AuthService
from app.services.user import UserService

router = APIRouter(prefix="/auth/v1", tags=["Authentication"])


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def signup(payload: SignupRequest, session: SessionDependency) -> User:
    return await AuthService(session).signup(payload)


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    session: SessionDependency,
) -> AuthResponse:
    result = await AuthService(session).login(payload)
    set_refresh_cookie(response, result.refresh_token)
    return AuthResponse(
        access_token=result.access_token,
        user=UserResponse.model_validate(result.user),
    )


@router.post("/refresh", response_model=AuthResponse)
async def refresh_access_token(
    request: Request,
    response: Response,
    session: SessionDependency,
) -> AuthResponse:
    result = await AuthService(session).refresh(
        request.cookies.get(REFRESH_COOKIE_NAME)
    )
    set_refresh_cookie(response, result.refresh_token)
    return AuthResponse(
        access_token=result.access_token,
        user=UserResponse.model_validate(result.user),
    )


@router.get("/me", response_model=UserResponse)
async def current_user(user: CurrentUser) -> User:
    return user


@router.patch("/me", response_model=UserResponse)
async def update_user(
    payload: UserUpdateRequest,
    user: CurrentUser,
    session: SessionDependency,
) -> User:
    return await UserService(session).update(user, payload)


@router.delete("/me", response_model=MessageResponse)
async def delete_user(
    response: Response,
    user: CurrentUser,
    session: SessionDependency,
) -> MessageResponse:
    await UserService(session).delete(user)
    clear_refresh_cookie(response)
    return MessageResponse(message="Account deleted")


@router.post("/logout", response_model=MessageResponse)
async def logout(
    response: Response,
    user: CurrentUser,
    session: SessionDependency,
) -> MessageResponse:
    await AuthService(session).logout_all(user)
    clear_refresh_cookie(response)
    return MessageResponse(message="Logged out from all sessions")
