from pathlib import Path
from typing import Any, Literal, cast

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application configuration loaded from environment variables and .env."""

    DATABASE_URL: str

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: Literal["HS256", "HS384", "HS512"] = "HS256"

    COOKIE_SECURE: bool = True
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"

    # Optional at startup; required only when S3-backed file operations are used.
    SUPABASE_S3_ENDPOINT: str | None = None
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_REGION: str = "auto"
    BUCKET_NAME: str | None = None
    MAX_UPLOAD_SIZE_BYTES: int = 100 * 1024 * 1024

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_settings(self) -> "Settings":
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
        if self.MAX_UPLOAD_SIZE_BYTES <= 0:
            raise ValueError("MAX_UPLOAD_SIZE_BYTES must be positive")
        return self

    def validate_storage_settings(self) -> None:
        required = {
            "SUPABASE_S3_ENDPOINT": self.SUPABASE_S3_ENDPOINT,
            "AWS_ACCESS_KEY_ID": self.AWS_ACCESS_KEY_ID,
            "AWS_SECRET_ACCESS_KEY": self.AWS_SECRET_ACCESS_KEY,
            "BUCKET_NAME": self.BUCKET_NAME,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise RuntimeError(
                "S3 storage is not configured; missing: " + ", ".join(missing)
            )


settings = cast(Any, Settings)()
