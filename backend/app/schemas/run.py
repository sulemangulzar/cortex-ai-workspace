from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import ExecutionLogSource, FindingSeverity, RunStatus, TaskStatus


class AgentTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    run_id: UUID
    agent_name: str
    status: TaskStatus
    revision_cycle: int
    started_at: datetime | None = None
    finished_at: datetime | None = None


class CodeFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    run_id: UUID
    path: str
    content: str
    revision_cycle: int


class ExecutionLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    run_id: UUID
    source: ExecutionLogSource
    content: str
    timestamp: datetime


class ReviewFindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    run_id: UUID
    reviewer_agent: str
    severity: FindingSeverity
    file_ref: str | None = None
    line_ref: int | None = None
    message: str
    resolved: bool
    revision_cycle: int


class RunSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    status: RunStatus
    revision_count: int
    started_at: datetime | None = None
    finished_at: datetime | None = None


class RunDetailResponse(RunSummaryResponse):
    agent_tasks: list[AgentTaskResponse] = []
    code_files: list[CodeFileResponse] = []
    review_findings: list[ReviewFindingResponse] = []
    execution_logs: list[ExecutionLogResponse] = []


class ActivityAgentTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    run_id: UUID
    agent_name: str
    status: TaskStatus
    revision_cycle: int
    started_at: datetime | None = None
    finished_at: datetime | None = None


class ActivityRunResponse(RunSummaryResponse):
    project_name: str
    agent_tasks: list[ActivityAgentTaskResponse] = []
    code_file_count: int = 0
    review_finding_count: int = 0
    execution_log_count: int = 0
