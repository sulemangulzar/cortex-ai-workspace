from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ProjectSourceStatus, SourceType


class ProjectSourceCreate(BaseModel):
    source_type: SourceType
    object_path: str = Field(min_length=1, max_length=1024)
    original_filename: str = Field(min_length=1, max_length=255)
    size_bytes: int = Field(ge=0)
    bucket: str = Field(default="cortex-workspace", min_length=1, max_length=255)
    status: ProjectSourceStatus = ProjectSourceStatus.uploading

    @field_validator("object_path", "original_filename", "bucket")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class ProjectSourceUpdate(BaseModel):
    original_filename: str | None = Field(default=None, min_length=1, max_length=255)
    size_bytes: int | None = Field(default=None, ge=0)
    bucket: str | None = Field(default=None, min_length=1, max_length=255)
    status: ProjectSourceStatus | None = None

    @field_validator("original_filename", "bucket")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class ProjectSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    source_type: SourceType
    bucket: str
    object_path: str
    original_filename: str
    size_bytes: int
    status: ProjectSourceStatus
    created_at: datetime


# Kept for compatibility with the existing upload flow.
SourceUploadRequest = ProjectSourceCreate


class SourceUploadResponse(BaseModel):
    source_id: UUID
    object_path: str
    upload_url: str
    token: str


class SourceCompleteRequest(BaseModel):
    source_id: UUID
