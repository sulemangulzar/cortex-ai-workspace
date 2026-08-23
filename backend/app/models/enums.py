from enum import Enum


class RunStatus(str, Enum):
    pending = "pending"
    running = "running"
    cancelled = "cancelled"
    needs_revision = "needs_revision"
    success = "success"
    failed = "failed"


class TaskStatus(str, Enum):
    pending = "pending"
    running = "running"
    success = "success"
    failed = "failed"
    cancelled = "cancelled"


class FindingSeverity(str, Enum):
    low = "low"
    med = "med"
    high = "high"
    critical = "critical"


class ExecutionLogSource(str, Enum):
    tool_output = "tool_output"
    agent_reasoning = "agent_reasoning"


class ChatMessageRole(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"
