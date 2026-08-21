from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import AsyncSessionFactory
from app.models.agent_step import AgentStep
from app.models.build_request import BuildRequest
from app.models.engineering_run import EngineeringRun
from app.models.enums import AgentStepStatus, AgentType, BuildRequestStatus, EngineeringRunStatus


AGENT_BRIEFS: tuple[tuple[AgentType, str, str], ...] = (
    (AgentType.feature_analyst, "Feature Analyst", "Clarify the requirement, users, scope, assumptions, and acceptance criteria."),
    (AgentType.architect, "Architect", "Design a pragmatic architecture, data model, API boundaries, and implementation risks."),
    (AgentType.developer, "Developer", "Turn the requirement and architecture into an implementation plan with concrete files and technical tasks."),
    (AgentType.qa, "QA Engineer", "Create a verification strategy with test cases, edge cases, and acceptance checks."),
    (AgentType.security_reviewer, "Security Reviewer", "Review the plan for authentication, authorization, secrets, data protection, and abuse risks."),
    (AgentType.performance_reviewer, "Performance Reviewer", "Review scalability, latency, resource usage, caching, and likely bottlenecks."),
    (AgentType.maintainability_reviewer, "Maintainability Reviewer", "Review code quality, modularity, observability, documentation, and operational complexity."),
    (AgentType.test_coverage_reviewer, "Test Coverage Reviewer", "Review test coverage gaps and produce a final quality checklist for delivery."),
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _text(result: Any) -> str:
    return str(getattr(result, "raw", result)).strip()


def _run_agent(agent_type: AgentType, name: str, brief: str, context: str) -> str:
    # Imports stay inside the worker so the API can still boot when CrewAI is unavailable.
    from crewai import Agent, Crew, LLM, Process, Task

    llm = LLM(model=settings.CREWAI_MODEL, api_key=settings.OPENAI_API_KEY)
    agent = Agent(
        role=name,
        goal=brief,
        backstory="You are a careful senior engineer working inside the Cortex engineering team.",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )
    task = Task(
        description=(
            f"Requirement and accumulated project context:\n{context}\n\n"
            f"Your stage ({agent_type.value}) must: {brief}\n"
            "Return a concise, structured response in Markdown with explicit decisions and risks."
        ),
        expected_output="A useful engineering deliverable with decisions, assumptions, and risks.",
        agent=agent,
    )
    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)
    return _text(crew.kickoff())


async def run_engineering_run(run_id: UUID) -> None:
    if AsyncSessionFactory is None:
        return

    async with AsyncSessionFactory() as session:
        run = await session.scalar(
            select(EngineeringRun)
            .options(selectinload(EngineeringRun.agent_steps), selectinload(EngineeringRun.build_request))
            .where(EngineeringRun.id == run_id)
        )
        if run is None:
            return

        request = run.build_request
        run.status = EngineeringRunStatus.running
        run.started_at = _now()
        run.current_stage = "FEATURE_ANALYST"
        request.status = BuildRequestStatus.processing
        await session.commit()

        try:
            if not settings.CREWAI_ENABLED:
                raise RuntimeError("CrewAI execution is disabled. Set CREWAI_ENABLED=true to enable builds.")
            if not settings.OPENAI_API_KEY:
                raise RuntimeError("OPENAI_API_KEY is not configured. Add it to backend/.env before starting a build.")

            context = request.requirement
            for agent_type, name, brief in AGENT_BRIEFS:
                step = next((item for item in run.agent_steps if item.agent_type == agent_type), None)
                if step is None:
                    step = AgentStep(engineering_run_id=run.id, agent_type=agent_type)
                    session.add(step)
                    await session.flush()

                step.status = AgentStepStatus.running
                step.started_at = _now()
                step.input_json = {"requirement": request.requirement, "context": context}
                run.current_stage = agent_type.value
                await session.commit()

                output = await asyncio.to_thread(_run_agent, agent_type, name, brief, context)
                step.status = AgentStepStatus.completed
                step.output_json = {"result": output}
                step.completed_at = _now()
                context = f"{context}\n\n## {name}\n{output}"

                if agent_type == AgentType.feature_analyst:
                    run.requirements_json = {"requirement": request.requirement, "analysis": output}
                elif agent_type == AgentType.architect:
                    run.architecture_json = {"architecture": output}
                elif agent_type in {
                    AgentType.security_reviewer,
                    AgentType.performance_reviewer,
                    AgentType.maintainability_reviewer,
                    AgentType.test_coverage_reviewer,
                }:
                    current_review = run.review_json or {}
                    current_review[agent_type.value.lower()] = output
                    run.review_json = current_review
                await session.commit()

            run.status = EngineeringRunStatus.completed
            run.current_stage = "COMPLETED"
            run.completed_at = _now()
            request.status = BuildRequestStatus.completed
            await session.commit()
        except Exception as exc:
            await session.rollback()
            run = await session.scalar(
                select(EngineeringRun).options(selectinload(EngineeringRun.agent_steps)).where(EngineeringRun.id == run_id)
            )
            request = await session.get(BuildRequest, run.build_request_id) if run else None
            if run is not None:
                run.status = EngineeringRunStatus.failed
                run.current_stage = "FAILED"
                run.error_message = str(exc)[:4000]
                run.completed_at = _now()
                for step in run.agent_steps:
                    if step.status == AgentStepStatus.running:
                        step.status = AgentStepStatus.failed
                        step.error_message = str(exc)[:4000]
                        step.completed_at = _now()
            if request is not None:
                request.status = BuildRequestStatus.failed
            await session.commit()
