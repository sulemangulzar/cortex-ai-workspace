from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any, Callable
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionFactory
from app.crew.agents import (
    ImplementationOutput,
    QAOutput,
    ReviewFindingSpec,
    run_architecture,
    run_feature_extraction,
    run_implementation,
    run_maintainability_review,
    run_performance_review,
    run_qa,
    run_security_review,
    run_test_coverage_review,
)
from app.crew.static_analysis import run_bandit, run_performance_static_scan
from app.models.agent_task import AgentTask
from app.models.architecture_doc import ArchitectureDoc
from app.models.chat import Chat
from app.models.code_file import CodeFile
from app.models.enums import ExecutionLogSource, FindingSeverity, RunStatus, TaskStatus
from app.models.execution_log import ExecutionLog
from app.models.feature import Feature
from app.models.requirement_doc import RequirementDoc
from app.models.review_finding import ReviewFinding
from app.models.run import Run
from app.services.realtime import realtime_manager

AGENT_NAMES = [
    "Requirements Analyst",
    "System Architect",
    "Implementation Developer",
    "QA Tester",
    "Security Reviewer",
    "Performance Reviewer",
    "Maintainability Reviewer",
    "Test Coverage Reviewer",
]

BLOCKING_SEVERITIES = {FindingSeverity.high, FindingSeverity.critical}


class PipelineCancelled(Exception):
    pass


class AgentPipelineService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_run(self, project_id: UUID) -> Run:
        previous_revision = await self.session.scalar(
            select(Run.revision_count)
            .where(Run.project_id == project_id)
            .order_by(Run.revision_count.desc())
            .limit(1)
        )
        run = Run(project_id=project_id, status=RunStatus.pending, revision_count=(previous_revision or -1) + 1)
        self.session.add(run)
        await self.session.flush()
        for agent_name in AGENT_NAMES:
            self.session.add(AgentTask(run_id=run.id, agent_name=agent_name, status=TaskStatus.pending))
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def execute(self, run_id: UUID) -> None:
        run = await self._load_run(run_id)
        if run is None:
            return

        await self._ensure_not_cancelled(run)
        run.status = RunStatus.running
        run.started_at = datetime.now(UTC)
        await self._log(run.id, ExecutionLogSource.agent_reasoning, "Agent pipeline started")
        await self.session.commit()
        await self._broadcast(run, "run.started", {"run_id": str(run.id), "status": run.status.value})

        try:
            previous_files = await self._latest_code_files(run.project_id, run.id)
            requirements_text = await self._build_requirements_context(run.project_id, previous_files)

            features = await self._run_task(
                run,
                "Requirements Analyst",
                {"requirements_text": requirements_text},
                lambda: run_feature_extraction(requirements_text),
            )
            for feature in features.features:
                self.session.add(
                    Feature(
                        run_id=run.id,
                        title=feature.title,
                        description=feature.description,
                        source_ref="requirements",
                    )
                )
            await self.session.commit()
            await self._broadcast(run, "features.saved", {"run_id": str(run.id), "count": len(features.features)})

            architecture = await self._run_task(
                run,
                "System Architect",
                {"requirements_text": requirements_text, "features": features.model_dump()},
                lambda: run_architecture(requirements_text, features.features),
            )
            self.session.add(ArchitectureDoc(run_id=run.id, content_json=architecture.model_dump(mode="json"), version=1))
            await self.session.commit()
            await self._broadcast(run, "architecture.saved", {"run_id": str(run.id)})

            implementation = await self._run_task(
                run,
                "Implementation Developer",
                {"requirements_text": requirements_text, "architecture": architecture.model_dump(mode="json")},
                lambda: run_implementation(requirements_text, architecture),
            )
            final_files = {**previous_files, **self._implementation_files(implementation)}
            for path, content in final_files.items():
                self.session.add(CodeFile(run_id=run.id, path=path, content=content, revision_cycle=run.revision_count))
            await self.session.commit()
            await self._broadcast(run, "code.saved", {"run_id": str(run.id), "count": len(final_files)})

            qa_plan = await self._run_task(
                run,
                "QA Tester",
                {
                    "requirements_text": requirements_text,
                    "architecture": architecture.model_dump(mode="json"),
                    "implementation": implementation.model_dump(mode="json"),
                },
                lambda: run_qa(requirements_text, architecture, implementation),
            )
            await self._persist_qa_blockers(run.id, qa_plan, run.revision_count)

            files_json = final_files
            bandit_output = run_bandit(files_json)
            security = await self._run_task(
                run,
                "Security Reviewer",
                {
                    "requirements_text": requirements_text,
                    "architecture": architecture.model_dump(mode="json"),
                    "implementation": implementation.model_dump(mode="json"),
                    "bandit": bandit_output,
                },
                lambda: run_security_review(requirements_text, architecture, implementation),
                tool_output=bandit_output,
            )
            await self._persist_findings(run.id, "Security Reviewer", security.findings, run.revision_count)

            performance_output = run_performance_static_scan(files_json)
            performance = await self._run_task(
                run,
                "Performance Reviewer",
                {
                    "requirements_text": requirements_text,
                    "architecture": architecture.model_dump(mode="json"),
                    "implementation": implementation.model_dump(mode="json"),
                    "performance_static": performance_output,
                },
                lambda: run_performance_review(requirements_text, architecture, implementation),
                tool_output=performance_output,
            )
            await self._persist_findings(run.id, "Performance Reviewer", performance.findings, run.revision_count)

            maintainability = await self._run_task(
                run,
                "Maintainability Reviewer",
                {
                    "requirements_text": requirements_text,
                    "architecture": architecture.model_dump(mode="json"),
                    "implementation": implementation.model_dump(mode="json"),
                },
                lambda: run_maintainability_review(requirements_text, architecture, implementation),
            )
            await self._persist_findings(run.id, "Maintainability Reviewer", maintainability.findings, run.revision_count)

            coverage = await self._run_task(
                run,
                "Test Coverage Reviewer",
                {
                    "requirements_text": requirements_text,
                    "architecture": architecture.model_dump(mode="json"),
                    "implementation": implementation.model_dump(mode="json"),
                    "qa_plan": qa_plan.model_dump(mode="json"),
                },
                lambda: run_test_coverage_review(requirements_text, architecture, implementation, qa_plan),
            )
            await self._persist_findings(run.id, "Test Coverage Reviewer", coverage.findings, run.revision_count)

            await self.session.refresh(run, attribute_names=["review_findings"])
            run.status = RunStatus.needs_revision if self._has_blocking_findings(run.review_findings) else RunStatus.success
            run.finished_at = datetime.now(UTC)
            await self._log(run.id, ExecutionLogSource.agent_reasoning, f"Agent pipeline finished with status={run.status.value}")
            await self.session.commit()
            await self._broadcast(run, "run.finished", {"run_id": str(run.id), "status": run.status.value})
        except PipelineCancelled:
            await self.session.rollback()
            cancelled_run = await self._load_run(run_id)
            if cancelled_run is not None:
                cancelled_run.status = RunStatus.cancelled
                cancelled_run.finished_at = datetime.now(UTC)
                for task in cancelled_run.agent_tasks:
                    if task.status in {TaskStatus.pending, TaskStatus.running}:
                        task.status = TaskStatus.cancelled
                await self._log(cancelled_run.id, ExecutionLogSource.agent_reasoning, "Agent pipeline stopped after cancellation")
                await self.session.commit()
                await self._broadcast(cancelled_run, "run.cancelled", {"run_id": str(cancelled_run.id), "status": cancelled_run.status.value})
        except Exception as exc:
            await self.session.rollback()
            failed_run = await self._load_run(run_id)
            if failed_run is not None and failed_run.status != RunStatus.cancelled:
                failed_run.status = RunStatus.failed
                failed_run.finished_at = datetime.now(UTC)
                await self._log(failed_run.id, ExecutionLogSource.tool_output, f"Agent pipeline failed: {type(exc).__name__}: {exc}")
                await self.session.commit()
                await self._broadcast(failed_run, "run.failed", {"run_id": str(failed_run.id), "status": failed_run.status.value, "error": str(exc)})
            raise

    async def _run_task(
        self,
        run: Run,
        agent_name: str,
        task_input: dict[str, Any],
        runner: Callable[[], BaseModel],
        tool_output: dict[str, Any] | None = None,
    ) -> Any:
        await self._ensure_not_cancelled(run)
        task = self._task_for(run, agent_name)
        now = datetime.now(UTC)
        task.status = TaskStatus.running
        task.started_at = now
        task.input = json.dumps(task_input, default=str)
        if tool_output is not None:
            task.tool_output = json.dumps(tool_output, default=str)
            finding_count = len(tool_output.get("findings", tool_output.get("results", []))) if isinstance(tool_output, dict) else 0
            await self._log(run.id, ExecutionLogSource.tool_output, f"{agent_name} tool completed with {finding_count} findings")
        await self._log(run.id, ExecutionLogSource.agent_reasoning, f"{agent_name} started")
        await self.session.commit()
        await self._broadcast(run, "agent.started", {"run_id": str(run.id), "agent_name": agent_name, "status": task.status.value})

        try:
            output = await asyncio.to_thread(runner)
            await self._ensure_not_cancelled(run)
        except PipelineCancelled:
            task.status = TaskStatus.cancelled
            task.finished_at = datetime.now(UTC)
            await self.session.commit()
            await self._broadcast(run, "agent.cancelled", {"run_id": str(run.id), "agent_name": agent_name, "status": task.status.value})
            raise
        except Exception as exc:
            task.status = TaskStatus.failed
            task.finished_at = datetime.now(UTC)
            task.tool_output = f"{type(exc).__name__}: {exc}"
            await self._log(run.id, ExecutionLogSource.tool_output, f"{agent_name} failed: {task.tool_output}")
            await self.session.commit()
            await self._broadcast(run, "agent.failed", {"run_id": str(run.id), "agent_name": agent_name, "status": task.status.value, "error": str(exc)})
            raise

        task.output = output.model_dump_json()
        task.status = TaskStatus.success
        task.finished_at = datetime.now(UTC)
        await self._log(run.id, ExecutionLogSource.agent_reasoning, f"{agent_name} completed")
        await self.session.commit()
        await self._broadcast(run, "agent.completed", {"run_id": str(run.id), "agent_name": agent_name, "status": task.status.value})
        return output

    def _task_for(self, run: Run, agent_name: str) -> AgentTask:
        for task in run.agent_tasks:
            if task.agent_name == agent_name:
                return task
        task = AgentTask(run_id=run.id, agent_name=agent_name, status=TaskStatus.pending)
        self.session.add(task)
        run.agent_tasks.append(task)
        return task

    async def _load_run(self, run_id: UUID) -> Run | None:
        return await self.session.scalar(
            select(Run)
            .options(selectinload(Run.project), selectinload(Run.agent_tasks), selectinload(Run.review_findings))
            .where(Run.id == run_id)
        )

    async def _build_requirements_context(self, project_id: UUID, previous_files: dict[str, str]) -> str:
        docs = list(await self.session.scalars(select(RequirementDoc).where(RequirementDoc.project_id == project_id).order_by(RequirementDoc.uploaded_at)))
        chat = await self.session.scalar(
            select(Chat).options(selectinload(Chat.messages)).where(Chat.project_id == project_id)
        )
        pieces: list[str] = []
        if docs:
            pieces.append("Uploaded requirement documents:")
            for doc in docs:
                pieces.append(f"\n--- {doc.file_path} ---\n{doc.raw_text}")
        if chat and chat.messages:
            pieces.append("\nFull chat history for this project. Treat the latest user message as the newest instruction and preserve earlier decisions unless the user changes them:")
            for index, message in enumerate(chat.messages, start=1):
                pieces.append(f"{index}. {message.role.value}: {message.content}")
        if previous_files:
            pieces.append("\nExisting generated project files from the previous run. Modify these files instead of starting from scratch. Return complete final contents for changed files:")
            for path, content in previous_files.items():
                pieces.append(f"\n--- FILE: {path} ---\n{content}")
        return "\n".join(pieces).strip() or "No requirements were provided. Ask for clarification and define only a minimal placeholder plan."

    async def _latest_code_files(self, project_id: UUID, current_run_id: UUID) -> dict[str, str]:
        previous_run = await self.session.scalar(
            select(Run)
            .join(CodeFile)
            .options(selectinload(Run.code_files))
            .where(Run.project_id == project_id, Run.id != current_run_id)
            .order_by(Run.finished_at.desc().nullslast(), Run.started_at.desc().nullslast(), Run.revision_count.desc())
            .limit(1)
        )
        if previous_run is None:
            return {}
        return {file.path: file.content for file in previous_run.code_files}

    def _implementation_files(self, implementation: ImplementationOutput) -> dict[str, str]:
        return {file.path: file.content for file in implementation.files}

    async def _persist_qa_blockers(self, run_id: UUID, qa_plan: QAOutput, revision_cycle: int) -> None:
        for blocker in qa_plan.release_blockers:
            self.session.add(
                ReviewFinding(
                    run_id=run_id,
                    reviewer_agent="QA Tester",
                    severity=FindingSeverity.high,
                    file_ref=None,
                    line_ref=None,
                    message=blocker,
                    resolved=False,
                    revision_cycle=revision_cycle,
                )
            )
        await self.session.commit()

    async def _persist_findings(
        self,
        run_id: UUID,
        reviewer_agent: str,
        findings: list[ReviewFindingSpec],
        revision_cycle: int,
    ) -> None:
        for finding in findings:
            severity = self._severity(finding.severity)
            self.session.add(
                ReviewFinding(
                    run_id=run_id,
                    reviewer_agent=reviewer_agent,
                    severity=severity,
                    file_ref=finding.file_ref,
                    line_ref=finding.line_ref,
                    message=f"{finding.message}\nRecommendation: {finding.recommendation}",
                    resolved=False,
                    revision_cycle=revision_cycle,
                )
            )
        await self.session.commit()

    def _severity(self, raw: str) -> FindingSeverity:
        normalized = raw.lower().strip()
        if normalized == "medium":
            normalized = "med"
        try:
            return FindingSeverity(normalized)
        except ValueError:
            return FindingSeverity.low

    def _has_blocking_findings(self, findings: list[ReviewFinding]) -> bool:
        return any(not finding.resolved and finding.severity in BLOCKING_SEVERITIES for finding in findings)

    async def _ensure_not_cancelled(self, run: Run) -> None:
        await self.session.refresh(run)
        if run.status == RunStatus.cancelled:
            raise PipelineCancelled()

    async def _log(self, run_id: UUID, source: ExecutionLogSource, content: str) -> None:
        self.session.add(ExecutionLog(run_id=run_id, source=source, content=content))

    async def _broadcast(self, run: Run, event: str, payload: dict[str, Any]) -> None:
        payload = {**payload, "project_id": str(run.project_id)}
        await realtime_manager.broadcast_project(run.project_id, event, payload)
        if run.project is not None:
            await realtime_manager.broadcast_user(run.project.user_id, event, payload)


async def run_project_agent_pipeline(run_id: UUID) -> None:
    if AsyncSessionFactory is None:
        return
    async with AsyncSessionFactory() as session:
        await AgentPipelineService(session).execute(run_id)
