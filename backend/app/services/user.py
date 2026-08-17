from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.models.user import User
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository
from app.schemas.auth import UserUpdateRequest


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)

    async def update(self, user: User, payload: UserUpdateRequest) -> User:
        updates = payload.model_dump(exclude_unset=True)
        if "email" in updates and updates["email"] is not None:
            updates["email"] = str(updates["email"])

        for field, value in updates.items():
            setattr(user, field, value)

        try:
            await self.session.commit()
            await self.session.refresh(user)
        except IntegrityError:
            await self.session.rollback()
            raise ConflictError("That email or username is already in use") from None
        return user

    async def delete(self, user: User) -> None:
        await self.refresh_tokens.delete_all_for_user(user.id)
        await self.users.delete(user)
        await self.session.commit()
