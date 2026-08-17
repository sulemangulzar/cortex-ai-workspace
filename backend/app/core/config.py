from typing import Any, Literal, cast

from pydantic import model_validator

from app.core.database_config import DatabaseSettings


class Settings(DatabaseSettings):
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: Literal["HS256", "HS384", "HS512"] = "HS256"
    COOKIE_SECURE: bool = True
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"

    @model_validator(mode="after")
    def validate_auth_settings(self) -> "Settings":
        if len(self.JWT_SECRET_KEY.encode("utf-8")) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 bytes long")
        if self.JWT_SECRET_KEY.lower() in {"secret", "changeme", "change-me"}:
            raise ValueError("JWT_SECRET_KEY must not use a default value")
        if self.ACCESS_TOKEN_EXPIRE_MINUTES <= 0:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be positive")
        if self.REFRESH_TOKEN_EXPIRE_MINUTES <= 0:
            raise ValueError("REFRESH_TOKEN_EXPIRE_MINUTES must be positive")
        if self.COOKIE_SAMESITE == "none" and not self.COOKIE_SECURE:
            raise ValueError("COOKIE_SECURE must be enabled when SameSite is 'none'")
        return self


# BaseSettings obtains these values from environment sources at runtime.
settings = cast(Any, Settings)()
