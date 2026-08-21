from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AgentStepStatus, AgentType, BuildRequestStatus, EngineeringRunStatus


class BuildCreate(BaseModel):
    requirement: str = Field(min_length=10, max_length=100_000)


class BuildRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    requirement: str
    requirements_document_key: str | None
    status: BuildRequestStatus
    created_at: datetime


class AgentStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    engineering_run_id: UUID
    agent_type: AgentType
    status: AgentStepStatus
    input_json: dict | None
    output_json: dict | None
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None


class EngineeringRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    build_request_id: UUID
    project_id: UUID
    status: EngineeringRunStatus
    current_stage: str | None
    requirements_json: dict | None
    architecture_json: dict | None
    review_json: dict | None
    output_storage_key: str | None
    fix_iteration: int
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    created_at: datetime
    agent_steps: list[AgentStepResponse] = []


class BuildResponse(BaseModel):
    request: BuildRequestResponse
    run: EngineeringRunResponse
