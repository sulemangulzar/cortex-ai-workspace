from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def add(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshToken:
        token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.session.add(token)
        return token

    async def get_by_hash(
        self, token_hash: str, *, for_update: bool = False
    ) -> RefreshToken | None:
        query = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        if for_update:
            query = query.with_for_update()
        return await self.session.scalar(query)

    async def delete(self, token: RefreshToken) -> None:
        await self.session.delete(token)

    async def delete_all_for_user(self, user_id: UUID) -> None:
        await self.session.execute(
            delete(RefreshToken).where(RefreshToken.user_id == user_id)
        )
