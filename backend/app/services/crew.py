from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import AsyncSessionFactory
from app.models.architecture_doc import ArchitectureDoc
from app.models.code_file import CodeFile
from app.models.execution_log import ExecutionLog
from app.models.feature import Feature
from app.models.review_finding import ReviewFinding
from app.models.run import Run
from app.models.enums import ExecutionLogSource, FindingSeverity, RunStatus, TaskStatus

AGENT_NAMES = (
    "FEATURE_ANALYST",
    "ARCHITECT",
    "DEVELOPER",
    "QA",
    "SECURITY_REVIEWER",
    "PERFORMANCE_REVIEWER",
    "MAINTAINABILITY_REVIEWER",
    "TEST_COVERAGE_REVIEWER",
)

AGENT_BRIEFS: dict[str, str] = {
    "FEATURE_ANALYST": "Clarify features, user goals, scope, assumptions, and acceptance criteria.",
    "ARCHITECT": "Design architecture, data model, API boundaries, and implementation risks.",
    "DEVELOPER": "Create an implementation plan and representative code file outputs.",
    "QA": "Create a verification strategy with test cases and edge cases.",
    "SECURITY_REVIEWER": "Review authentication, authorization, secrets, data protection, and abuse risks.",
    "PERFORMANCE_REVIEWER": "Review scalability, latency, resource usage, caching, and bottlenecks.",
    "MAINTAINABILITY_REVIEWER": "Review modularity, observability, documentation, and operational complexity.",
    "TEST_COVERAGE_REVIEWER": "Review test coverage gaps and final delivery checklist.",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _text(result: Any) -> str:
    return str(getattr(result, "raw", result)).strip()


def _run_agent(agent_name: str, context: str) -> str:
    from crewai import Agent, Crew, LLM, Process, Task

    llm = LLM(model=settings.CREWAI_MODEL, api_key=settings.OPENAI_API_KEY)
    brief = AGENT_BRIEFS[agent_name]
    agent = Agent(
        role=agent_name.replace("_", " ").title(),
        goal=brief,
        backstory="You are a senior AI engineering agent working inside Cortex.",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )
    task = Task(
        description=(
            f"Context so far:\n{context}\n\n"
            f"Your responsibility: {brief}\n"
            "Return concise Markdown with decisions, outputs, risks, and next actions."
        ),
        expected_output="Structured Markdown output for this agent stage.",
        agent=agent,
    )
    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)
    return _text(crew.kickoff())


async def run_engineering_run(run_id: UUID) -> None:
    if AsyncSessionFactory is None:
        return

    async with AsyncSessionFactory() as session:
        run = await session.scalar(select(Run).options(selectinload(Run.agent_tasks)).where(Run.id == run_id))
        if run is None:
            return

        run.status = RunStatus.running
        run.started_at = _now()
        await session.commit()

        try:
            if not settings.CREWAI_ENABLED:
                raise RuntimeError("CrewAI execution is disabled. Set CREWAI_ENABLED=true.")
            if not settings.OPENAI_API_KEY:
                raise RuntimeError("OPENAI_API_KEY is not configured in backend/.env.")

            context = next((task.input for task in run.agent_tasks if task.input), "")
            for task in sorted(run.agent_tasks, key=lambda item: AGENT_NAMES.index(item.agent_name)):
                task.status = TaskStatus.running
                task.started_at = _now()
                await session.commit()

                try:
                    output = await asyncio.to_thread(_run_agent, task.agent_name, context)
                except Exception as exc:
                    task.status = TaskStatus.failed
                    task.tool_output = str(exc)[:8000]
                    task.finished_at = _now()
                    run.status = RunStatus.failed
                    run.finished_at = _now()
                    session.add(ExecutionLog(run_id=run.id, source=ExecutionLogSource.tool_output, content=str(exc)[:8000]))
                    await session.commit()
                    return

                task.output = output
                task.status = TaskStatus.success
                task.finished_at = _now()
                context = f"{context}\n\n## {task.agent_name}\n{output}"
                session.add(ExecutionLog(run_id=run.id, source=ExecutionLogSource.agent_reasoning, content=f"{task.agent_name}\n{output}"))

                if task.agent_name == "FEATURE_ANALYST":
                    session.add(Feature(run_id=run.id, title="Initial Feature Set", description=output, source_ref="FEATURE_ANALYST"))
                elif task.agent_name == "ARCHITECT":
                    session.add(ArchitectureDoc(run_id=run.id, content_json={"markdown": output}, version=1))
                elif task.agent_name == "DEVELOPER":
                    session.add(CodeFile(run_id=run.id, path="PLAN.md", content=output, revision_cycle=task.revision_cycle))
                elif "REVIEWER" in task.agent_name or task.agent_name == "QA":
                    severity = FindingSeverity.med if "risk" in output.lower() or "issue" in output.lower() else FindingSeverity.low
                    session.add(ReviewFinding(run_id=run.id, reviewer_agent=task.agent_name, severity=severity, message=output[:4000], revision_cycle=task.revision_cycle))
                await session.commit()

            unresolved = await session.scalar(
                select(ReviewFinding.id).where(ReviewFinding.run_id == run.id, ReviewFinding.resolved.is_(False), ReviewFinding.severity.in_([FindingSeverity.high, FindingSeverity.critical]))
            )
            run.status = RunStatus.needs_revision if unresolved else RunStatus.success
            run.finished_at = _now()
            await session.commit()
        except Exception as exc:
            await session.rollback()
            run = await session.scalar(select(Run).where(Run.id == run_id))
            if run is not None:
                run.status = RunStatus.failed
                run.finished_at = _now()
                session.add(ExecutionLog(run_id=run.id, source=ExecutionLogSource.tool_output, content=str(exc)[:8000]))
                await session.commit()
