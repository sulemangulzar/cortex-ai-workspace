from typing import Any, cast

from app.core.database_config import DatabaseSettings


class Settings(DatabaseSettings):
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_MINUTES: int
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    COOKIE_SECURE: bool = True
    COOKIE_SAMESITE: str = "lax"


# BaseSettings obtains these values from environment sources at runtime.
settings = cast(Any, Settings)()
