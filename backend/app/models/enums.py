# enums.py

from enum import Enum


class ProjectStatus(str, Enum):
    created = "CREATED"
    ready = "READY"
    processing = "PROCESSING"
    completed = "COMPLETED"
    failed = "FAILED"

class BuildRequestStatus(str, Enum):
    pending = "PENDING"
    processing = "PROCESSING"
    completed = "COMPLETED"
    failed = "FAILED"


class EngineeringRunStatus(str, Enum):
    pending = "PENDING"
    running = "RUNNING"
    completed = "COMPLETED"
    failed = "FAILED"
    cancelled = "CANCELLED"


class AgentStepStatus(str, Enum):
    pending = "PENDING"
    running = "RUNNING"
    completed = "COMPLETED"
    failed = "FAILED"
    skipped = "SKIPPED"


class AgentType(str, Enum):
    feature_analyst = "FEATURE_ANALYST"
    architect = "ARCHITECT"
    developer = "DEVELOPER"
    qa = "QA"
    security_reviewer = "SECURITY_REVIEWER"
    performance_reviewer = "PERFORMANCE_REVIEWER"
    maintainability_reviewer = "MAINTAINABILITY_REVIEWER"
    test_coverage_reviewer = "TEST_COVERAGE_REVIEWER"


class Roles(str, Enum):
    system = "SYSTEM"
    assistant = "ASSISTANT"
    user = "USER"

class ProjectSourceStatus(str, Enum):
    uploading = "UPLOADING"
    uploaded = "UPLOADED"
    failed = "FAILED"


class SourceType(str, Enum):
    zip = "ZIP"
    github_repo = "GITHUB_REPOSITORY"
