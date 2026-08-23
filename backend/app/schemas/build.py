from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models.enums import FindingSeverity, RunStatus, TaskStatus


class BuildCreate(BaseModel):
    requirement: str = Field(min_length=10, max_length=100_000)


class AgentTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    run_id: UUID
    agent_name: str
    status: TaskStatus
    input: str | None
    output: str | None
    tool_output: str | None
    revision_cycle: int
    started_at: datetime | None
    finished_at: datetime | None


class ReviewFindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    run_id: UUID
    reviewer_agent: str
    severity: FindingSeverity
    file_ref: str | None
    line_ref: int | None
    message: str
    resolved: bool
    revision_cycle: int


class RunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    celery_task_id: str | None
    status: RunStatus
    revision_count: int
    started_at: datetime | None
    finished_at: datetime | None
    agent_tasks: list[AgentTaskResponse] = []
    review_findings: list[ReviewFindingResponse] = []

    @computed_field
    @property
    def current_stage(self) -> str | None:
        running = next((task.agent_name for task in self.agent_tasks if task.status == TaskStatus.running), None)
        if running is not None:
            return running
        pending = next((task.agent_name for task in self.agent_tasks if task.status == TaskStatus.pending), None)
        return pending

    @computed_field
    @property
    def error_message(self) -> str | None:
        failed = next((task for task in self.agent_tasks if task.status == TaskStatus.failed), None)
        return failed.tool_output if failed is not None else None


class BuildResponse(BaseModel):
    run: RunResponse


EngineeringRunResponse = RunResponse
