# enums.py

from enum import Enum


class ProjectStatus(str, Enum):
    created = "CREATED"
    ready = "READY"
    processing = "PROCESSING"
    completed = "COMPLETED"
    failed = "FAILED"


class ProjectSourceStatus(str, Enum):
    uploading = "UPLOADING"
    uploaded = "UPLOADED"
    failed = "FAILED"


class SourceType(str, Enum):
    zip = "ZIP"
    github_repo = "GITHUB_REPOSITORY"
