from __future__ import annotations

import json
from typing import cast

from pydantic import BaseModel, Field
from crewai import Agent, Crew, LLM, Process, Task
from crewai.tools import tool

from app.core.config import settings
from app.crew.static_analysis import run_bandit, run_performance_static_scan

# CrewAI's LLM class wraps LiteLLM under the hood. Keep simple agents cheap/fast;
# later reviewer agents can use a stronger model if needed.
cheap_llm = LLM(
    model=settings.CREWAI_MODEL or "openai/gpt-4o-mini",
    api_key=settings.OPENAI_API_KEY,
    temperature=0.2,
)


class FeatureItem(BaseModel):
    title: str = Field(description="Short buildable feature title")
    description: str = Field(description="Concrete feature behavior and scope")


class FeatureExtractionOutput(BaseModel):
    features: list[FeatureItem] = Field(description="Concrete features implied by the requirements")
    assumptions: list[str] = Field(default_factory=list, description="Assumptions made for ambiguous requirements")


class DataModelSpec(BaseModel):
    name: str = Field(description="Entity/table/model name")
    purpose: str = Field(description="Why this model exists")
    fields: list[str] = Field(description="Important fields needed by implementation")


class ApiEndpointSpec(BaseModel):
    method: str = Field(description="HTTP method such as GET, POST, PATCH, DELETE")
    path: str = Field(description="Endpoint path")
    purpose: str = Field(description="What this endpoint does")
    request_shape: str | None = Field(default=None, description="Important request fields")
    response_shape: str | None = Field(default=None, description="Important response fields")


class ArchitectureOutput(BaseModel):
    system_summary: str = Field(description="High-level architecture summary")
    frontend_components: list[str] = Field(description="Frontend pages/components needed")
    backend_services: list[str] = Field(description="Backend services/modules needed")
    data_models: list[DataModelSpec] = Field(description="Data structures needed by the DB and next agents")
    api_endpoints: list[ApiEndpointSpec] = Field(description="API contract required for implementation")
    background_jobs: list[str] = Field(default_factory=list, description="Async/background tasks, workers, queues, or schedulers")
    storage_needs: list[str] = Field(default_factory=list, description="File/object/database storage needs")
    auth_and_permissions: list[str] = Field(default_factory=list, description="Auth, ownership, and authorization rules")
    external_integrations: list[str] = Field(default_factory=list, description="External APIs, services, tools, or libraries")
    implementation_order: list[str] = Field(description="Recommended build sequence for the developer agent")
    risks: list[str] = Field(default_factory=list, description="Architectural risks or unclear requirements")
    assumptions: list[str] = Field(default_factory=list, description="Explicit assumptions for sparse or ambiguous inputs")


class CodeFileSpec(BaseModel):
    path: str = Field(description="Repository-relative file path the developer agent proposes to create or edit")
    purpose: str = Field(description="Why this file is needed")
    content: str = Field(description="Representative implementation content or detailed pseudocode for the file")
    depends_on: list[str] = Field(default_factory=list, description="Other files, services, or packages this file depends on")


class ImplementationOutput(BaseModel):
    implementation_summary: str = Field(description="Concise summary of the implementation approach")
    files: list[CodeFileSpec] = Field(description="Files needed by the developer to implement the system")
    database_changes: list[str] = Field(default_factory=list, description="Schema or migration work required")
    api_implementation_notes: list[str] = Field(default_factory=list, description="Endpoint/service implementation details")
    frontend_implementation_notes: list[str] = Field(default_factory=list, description="UI/component implementation details")
    background_job_notes: list[str] = Field(default_factory=list, description="Worker, queue, or async processing details")
    environment_variables: list[str] = Field(default_factory=list, description="Required environment variables or secrets")
    commands_to_run: list[str] = Field(default_factory=list, description="Build, migration, lint, or test commands")
    handoff_notes_for_qa: list[str] = Field(description="Specific areas QA should verify")
    assumptions: list[str] = Field(default_factory=list, description="Assumptions made while implementing sparse input")
    risks: list[str] = Field(default_factory=list, description="Implementation risks or missing decisions")


class TestCaseSpec(BaseModel):
    name: str = Field(description="Human-readable test case name")
    type: str = Field(description="unit, integration, e2e, security, performance, or manual")
    target: str = Field(description="Feature, endpoint, component, file, or flow under test")
    steps: list[str] = Field(description="Concrete actions to execute")
    expected_result: str = Field(description="Observable pass condition")
    priority: str = Field(description="low, medium, high, or critical")


class QAOutput(BaseModel):
    qa_summary: str = Field(description="Overall QA strategy and confidence notes")
    acceptance_checks: list[str] = Field(description="Product-level checks required before release")
    test_cases: list[TestCaseSpec] = Field(description="Concrete tests to run or automate")
    automation_commands: list[str] = Field(default_factory=list, description="Commands QA/developer should run")
    edge_cases: list[str] = Field(default_factory=list, description="Edge cases and sparse-input behavior to verify")
    regression_risks: list[str] = Field(default_factory=list, description="Existing behavior that could break")
    missing_requirements: list[str] = Field(default_factory=list, description="Questions or gaps QA cannot verify from available input")
    release_blockers: list[str] = Field(default_factory=list, description="Issues that must be fixed before release")


class ReviewFindingSpec(BaseModel):
    category: str = Field(description="Finding category such as injection, auth, n+1, allocation, or complexity")
    severity: str = Field(description="low, med, high, or critical")
    file_ref: str | None = Field(default=None, description="Relevant file path if known")
    line_ref: int | None = Field(default=None, description="Relevant line number if known")
    message: str = Field(description="Clear finding message")
    recommendation: str = Field(description="Concrete remediation guidance")
    blocks_release: bool = Field(description="Whether this finding should block release")


class SecurityReviewOutput(BaseModel):
    review_summary: str = Field(description="Overall security posture summary")
    findings: list[ReviewFindingSpec] = Field(description="Security findings suitable for review_findings storage")
    injection_risks: list[str] = Field(default_factory=list, description="Prompt/SQL/command/path injection risks")
    auth_risks: list[str] = Field(default_factory=list, description="Authentication, authorization, session, and ownership risks")
    secret_risks: list[str] = Field(default_factory=list, description="Secret storage/exposure/configuration risks")
    unsafe_deserialization_risks: list[str] = Field(default_factory=list, description="Unsafe parsing/deserialization/file handling risks")
    required_controls: list[str] = Field(default_factory=list, description="Security controls the developer must implement")
    secure_defaults: list[str] = Field(default_factory=list, description="Safe defaults/configuration requirements")
    assumptions: list[str] = Field(default_factory=list, description="Security assumptions made due to missing detail")


class PerformanceReviewOutput(BaseModel):
    review_summary: str = Field(description="Overall performance posture summary")
    findings: list[ReviewFindingSpec] = Field(description="Performance findings suitable for review_findings storage")
    complexity_risks: list[str] = Field(default_factory=list, description="Algorithmic or architectural complexity risks")
    n_plus_one_risks: list[str] = Field(default_factory=list, description="Potential N+1 query or repeated network call risks")
    allocation_hot_path_risks: list[str] = Field(default_factory=list, description="Avoidable allocations/memory pressure in hot paths")
    caching_opportunities: list[str] = Field(default_factory=list, description="Where caching, batching, pagination, or streaming helps")
    observability_requirements: list[str] = Field(default_factory=list, description="Metrics/logs/traces needed to detect bottlenecks")
    load_test_scenarios: list[str] = Field(default_factory=list, description="Performance scenarios QA should test")
    assumptions: list[str] = Field(default_factory=list, description="Performance assumptions made due to missing detail")


class MaintainabilityReviewOutput(BaseModel):
    review_summary: str = Field(description="Overall maintainability posture summary")
    findings: list[ReviewFindingSpec] = Field(description="Maintainability findings suitable for review_findings storage")
    naming_issues: list[str] = Field(default_factory=list, description="Unclear, inconsistent, misleading, or leaky names")
    coupling_issues: list[str] = Field(default_factory=list, description="Tight coupling, poor boundaries, or dependency direction issues")
    dead_abstractions: list[str] = Field(default_factory=list, description="Premature abstractions, unused layers, dead interfaces, or generic code without value")
    module_boundary_recommendations: list[str] = Field(default_factory=list, description="How to split, merge, or clarify modules")
    refactor_plan: list[str] = Field(default_factory=list, description="Ordered, concrete refactoring actions")
    documentation_gaps: list[str] = Field(default_factory=list, description="Docs/comments/API contracts needed for maintainability")
    assumptions: list[str] = Field(default_factory=list, description="Maintainability assumptions made due to missing detail")


class CoverageGapSpec(BaseModel):
    target: str = Field(description="Feature, endpoint, component, file, or behavior with missing coverage")
    gap: str = Field(description="What is untested or insufficiently tested")
    recommended_test: str = Field(description="Concrete test to add")
    test_type: str = Field(description="unit, integration, e2e, contract, security, performance, or manual")
    priority: str = Field(description="low, medium, high, or critical")


class UntestableItemSpec(BaseModel):
    target: str = Field(description="Code/behavior that is hard or impossible to test as written")
    reason: str = Field(description="Why it is untestable or difficult to isolate")
    required_change: str = Field(description="Refactor, seam, dependency injection, or API change needed to make it testable")


class TestCoverageReviewOutput(BaseModel):
    review_summary: str = Field(description="Overall test coverage posture summary")
    findings: list[ReviewFindingSpec] = Field(description="Coverage findings suitable for review_findings storage")
    coverage_gaps: list[CoverageGapSpec] = Field(description="Specific untested or undertested areas")
    untestable_items: list[UntestableItemSpec] = Field(default_factory=list, description="Things untestable as currently written")
    minimum_test_suite: list[str] = Field(default_factory=list, description="Minimum test suite required before release")
    automation_commands: list[str] = Field(default_factory=list, description="Commands to run coverage/test checks")
    coverage_metrics_to_track: list[str] = Field(default_factory=list, description="Coverage or quality metrics to monitor")
    assumptions: list[str] = Field(default_factory=list, description="Coverage assumptions made due to missing detail")


@tool("Bandit Security Scanner")
def bandit_scan(files_json: str) -> str:
    """Runs Bandit static analysis on generated code files. Input: JSON {filename: content}."""
    try:
        files = json.loads(files_json)
        if not isinstance(files, dict):
            return json.dumps({"scanner": "bandit", "error": "Input must be a JSON object mapping filenames to content"})
        return json.dumps(run_bandit(files))
    except Exception as exc:
        return json.dumps({"scanner": "bandit", "error": str(exc)})


@tool("Performance Static Scanner")
def performance_scan(files_json: str) -> str:
    """Runs lightweight performance static analysis on generated code files. Input: JSON {filename: content}."""
    try:
        files = json.loads(files_json)
        if not isinstance(files, dict):
            return json.dumps({"scanner": "performance_static", "error": "Input must be a JSON object mapping filenames to content"})
        return json.dumps(run_performance_static_scan(files))
    except Exception as exc:
        return json.dumps({"scanner": "performance_static", "error": str(exc)})


feature_extractor = Agent(
    role="Requirements Analyst",
    goal=(
        "Read raw requirements text and extract a complete, unambiguous list of "
        "concrete features a dev team can build against."
    ),
    backstory=(
        "You've spent years turning messy client requirements into buildable specs. "
        "You never invent features that weren't implied by the text. If something is "
        "ambiguous, you note it as an assumption rather than guessing silently."
    ),
    llm=cheap_llm,
    allow_delegation=False,
    verbose=True,
)

architect = Agent(
    role="System Architect",
    goal=(
        "Architect a practical software system for the required features. Produce the "
        "contracts and structure the developer, QA, and database layers actually need."
    ),
    backstory=(
        "You are a senior full-stack architect who turns product features into clear, "
        "minimal, production-minded system designs. You optimize for correctness, "
        "ownership boundaries, maintainability, and implementation clarity. When input "
        "is sparse, you keep the design lean and mark assumptions explicitly."
    ),
    llm=cheap_llm,
    allow_delegation=False,
    verbose=True,
)

developer = Agent(
    role="Implementation Developer",
    goal=(
        "Transform requirements and architecture into a concrete implementation package: "
        "files, code-level structure, database changes, commands, and QA handoff notes."
    ),
    backstory=(
        "You are a pragmatic senior full-stack developer. You write implementation plans "
        "that another coding agent can apply directly. You avoid vague advice, avoid "
        "unnecessary abstractions, and call out assumptions when product input is sparse."
    ),
    llm=cheap_llm,
    allow_delegation=False,
    verbose=True,
)

qa_tester = Agent(
    role="QA Tester",
    goal=(
        "Verify that the implemented system satisfies the requirements and architecture. "
        "Produce concrete acceptance checks, test cases, automation commands, edge cases, "
        "and release blockers."
    ),
    backstory=(
        "You are a detail-oriented QA engineer who catches ambiguous requirements, broken "
        "flows, missing validations, and regression risks. You design tests that are useful "
        "to both humans and automated test agents."
    ),
    llm=cheap_llm,
    allow_delegation=False,
    verbose=True,
)

security_reviewer = Agent(
    role="Security Reviewer",
    goal=(
        "Review the architecture and implementation for injection risks, authentication "
        "and authorization flaws, secret exposure, unsafe deserialization, and unsafe file handling."
    ),
    backstory=(
        "You are an application security engineer who focuses on practical exploit paths. "
        "You flag concrete risks with severity, file/endpoint references when possible, and "
        "specific remediations. You do not invent vulnerabilities without a plausible path; "
        "when details are missing, you state the assumption and required control."
    ),
    llm=cheap_llm,
    allow_delegation=False,
    tools=[bandit_scan],
    verbose=True,
)

performance_reviewer = Agent(
    role="Performance Reviewer",
    goal=(
        "Review the architecture and implementation for complexity problems, N+1 queries, "
        "repeated network calls, and unnecessary allocation in hot paths."
    ),
    backstory=(
        "You are a performance-minded backend/full-stack engineer. You look for bottlenecks "
        "that will appear under real user load: database access patterns, large file processing, "
        "memory pressure, synchronous work in request paths, missing pagination, and missing metrics."
    ),
    llm=cheap_llm,
    allow_delegation=False,
    tools=[performance_scan],
    verbose=True,
)

maintainability_reviewer = Agent(
    role="Maintainability Reviewer",
    goal=(
        "Review the architecture and implementation for naming problems, tight coupling, "
        "dead abstractions, unclear boundaries, and long-term code ownership risks."
    ),
    backstory=(
        "You are a senior engineer who keeps systems simple. You identify misleading names, "
        "over-engineered layers, hidden coupling, duplicated concepts, and abstractions that "
        "do not pay for themselves. Your recommendations are small, concrete, and safe."
    ),
    llm=cheap_llm,
    allow_delegation=False,
    verbose=True,
)

test_coverage_reviewer = Agent(
    role="Test Coverage Reviewer",
    goal=(
        "Review what is untested, undertested, or untestable as written. Produce concrete "
        "coverage gaps, test cases to add, and refactors needed for testability."
    ),
    backstory=(
        "You are a test strategy specialist. You care less about vanity coverage and more "
        "about meaningful confidence in critical behavior. You call out code that cannot be "
        "tested cleanly because dependencies, side effects, or boundaries are poorly designed."
    ),
    llm=cheap_llm,
    allow_delegation=False,
    verbose=True,
)


def build_feature_extraction_task(requirements_text: str) -> Task:
    return Task(
        description=(
            f"Requirements:\n{requirements_text}\n\n"
            "Extract concrete features implied by this text. Do not invent features. "
            "If something is ambiguous, capture it as an assumption."
        ),
        expected_output="A structured feature extraction object.",
        output_pydantic=FeatureExtractionOutput,
        agent=feature_extractor,
    )


def build_architecture_task(requirements_text: str, features: list[FeatureItem] | None = None) -> Task:
    feature_context = "\n".join(
        f"- {feature.title}: {feature.description}" for feature in (features or [])
    ) or "No extracted feature list was provided; infer only from the requirements text."

    return Task(
        description=(
            "Architect the system for the required features.\n\n"
            f"Raw requirements:\n{requirements_text}\n\n"
            f"Feature context:\n{feature_context}\n\n"
            "Design only what the next developer agent and the database actually need. "
            "Prefer a lean architecture over unnecessary services. Include assumptions "
            "for sparse inputs instead of over-specifying."
        ),
        expected_output=(
            "A typed architecture object containing system summary, frontend components, "
            "backend services, data models, API endpoints, jobs, storage, auth rules, "
            "implementation order, risks, and assumptions."
        ),
        output_pydantic=ArchitectureOutput,
        agent=architect,
    )


def _architecture_context(architecture: ArchitectureOutput | None) -> str:
    if architecture is None:
        return "No architecture object was provided; infer a minimal implementation from the requirements."
    return architecture.model_dump_json(indent=2)


def _implementation_context(implementation: ImplementationOutput | None) -> str:
    if implementation is None:
        return "No implementation object was provided; design QA from requirements and architecture only."
    return implementation.model_dump_json(indent=2)


def build_implementation_task(requirements_text: str, architecture: ArchitectureOutput | None = None) -> Task:
    return Task(
        description=(
            "Implement/develop the system described by the requirements and architecture.\n\n"
            f"Raw requirements:\n{requirements_text}\n\n"
            f"Architecture context:\n{_architecture_context(architecture)}\n\n"
            "Return only what the next coding/runtime layer and QA actually need: files, "
            "representative content, database changes, commands, environment variables, "
            "and QA handoff notes. If existing generated files are included in the context, "
            "modify those files instead of restarting from scratch. Return complete final "
            "contents for any changed file. For sparse inputs, produce a small but complete MVP."
        ),
        expected_output=(
            "A typed implementation object containing implementation summary, files, DB changes, "
            "API/frontend/background notes, env vars, commands, QA handoff notes, assumptions, and risks."
        ),
        output_pydantic=ImplementationOutput,
        agent=developer,
    )


def build_qa_task(
    requirements_text: str,
    architecture: ArchitectureOutput | None = None,
    implementation: ImplementationOutput | None = None,
) -> Task:
    return Task(
        description=(
            "Create a QA test plan for the system.\n\n"
            f"Raw requirements:\n{requirements_text}\n\n"
            f"Architecture context:\n{_architecture_context(architecture)}\n\n"
            f"Implementation context:\n{_implementation_context(implementation)}\n\n"
            "Focus on concrete acceptance checks, executable test cases, edge cases, "
            "automation commands, missing requirements, and release blockers. Do not mark "
            "unknown behavior as passed; list it as a missing requirement or risk."
        ),
        expected_output=(
            "A typed QA object containing QA summary, acceptance checks, test cases, commands, "
            "edge cases, regression risks, missing requirements, and release blockers."
        ),
        output_pydantic=QAOutput,
        agent=qa_tester,
    )


def build_security_review_task(
    requirements_text: str,
    architecture: ArchitectureOutput | None = None,
    implementation: ImplementationOutput | None = None,
) -> Task:
    return Task(
        description=(
            "Perform a security review for this system.\n\n"
            f"Raw requirements:\n{requirements_text}\n\n"
            f"Architecture context:\n{_architecture_context(architecture)}\n\n"
            f"Implementation context:\n{_implementation_context(implementation)}\n\n"
            "Focus specifically on injection risks, auth/authorization/session ownership, "
            "secret exposure, unsafe deserialization/parsing, unsafe file upload handling, "
            "and dangerous tool execution. If implementation files are present, call the "
            "Bandit Security Scanner tool with a JSON object mapping paths to file content, "
            "then incorporate real scanner findings into the review. Produce findings that "
            "can be stored in review_findings."
        ),
        expected_output=(
            "A typed security review object with summary, findings, injection risks, auth risks, "
            "secret risks, unsafe deserialization risks, required controls, secure defaults, and assumptions."
        ),
        output_pydantic=SecurityReviewOutput,
        agent=security_reviewer,
    )


def build_performance_review_task(
    requirements_text: str,
    architecture: ArchitectureOutput | None = None,
    implementation: ImplementationOutput | None = None,
) -> Task:
    return Task(
        description=(
            "Perform a performance review for this system.\n\n"
            f"Raw requirements:\n{requirements_text}\n\n"
            f"Architecture context:\n{_architecture_context(architecture)}\n\n"
            f"Implementation context:\n{_implementation_context(implementation)}\n\n"
            "Focus specifically on complexity, N+1 database queries, repeated network/storage calls, "
            "large allocations or blocking work in hot paths, missing pagination/streaming, caching, "
            "and observability. If implementation files are present, call the Performance Static "
            "Scanner tool with a JSON object mapping paths to file content, then incorporate real "
            "scanner findings into the review. Produce findings that can be stored in review_findings."
        ),
        expected_output=(
            "A typed performance review object with summary, findings, complexity risks, N+1 risks, "
            "allocation hot-path risks, caching opportunities, observability needs, load tests, and assumptions."
        ),
        output_pydantic=PerformanceReviewOutput,
        agent=performance_reviewer,
    )


def build_maintainability_review_task(
    requirements_text: str,
    architecture: ArchitectureOutput | None = None,
    implementation: ImplementationOutput | None = None,
) -> Task:
    return Task(
        description=(
            "Perform a maintainability review for this system.\n\n"
            f"Raw requirements:\n{requirements_text}\n\n"
            f"Architecture context:\n{_architecture_context(architecture)}\n\n"
            f"Implementation context:\n{_implementation_context(implementation)}\n\n"
            "Focus specifically on naming, coupling, module boundaries, dead abstractions, "
            "duplicated concepts, unclear ownership, and long-term readability. Produce findings "
            "that can be stored in review_findings and a concrete refactor plan."
        ),
        expected_output=(
            "A typed maintainability review object with summary, findings, naming issues, coupling issues, "
            "dead abstractions, boundary recommendations, refactor plan, docs gaps, and assumptions."
        ),
        output_pydantic=MaintainabilityReviewOutput,
        agent=maintainability_reviewer,
    )


def build_test_coverage_review_task(
    requirements_text: str,
    architecture: ArchitectureOutput | None = None,
    implementation: ImplementationOutput | None = None,
    qa_plan: QAOutput | None = None,
) -> Task:
    qa_context = qa_plan.model_dump_json(indent=2) if qa_plan is not None else "No QA plan was provided; infer coverage needs from requirements, architecture, and implementation."
    return Task(
        description=(
            "Perform a test coverage review for this system.\n\n"
            f"Raw requirements:\n{requirements_text}\n\n"
            f"Architecture context:\n{_architecture_context(architecture)}\n\n"
            f"Implementation context:\n{_implementation_context(implementation)}\n\n"
            f"QA context:\n{qa_context}\n\n"
            "Identify what is untested, undertested, and untestable as written. Focus on meaningful "
            "behavioral coverage, not vanity line coverage. If something cannot be tested without a "
            "design change, list it as an untestable item with the required refactor."
        ),
        expected_output=(
            "A typed test coverage review object with summary, findings, coverage gaps, untestable items, "
            "minimum test suite, automation commands, metrics, and assumptions."
        ),
        output_pydantic=TestCoverageReviewOutput,
        agent=test_coverage_reviewer,
    )


def run_feature_extraction(requirements_text: str) -> FeatureExtractionOutput:
    crew = Crew(
        agents=[feature_extractor],
        tasks=[build_feature_extraction_task(requirements_text)],
        process=Process.sequential,
    )
    result = crew.kickoff()
    output = getattr(result, "pydantic", None)
    if output is None:
        raise RuntimeError("Feature extraction did not return a Pydantic output")
    return cast(FeatureExtractionOutput, output)


def run_architecture(requirements_text: str, features: list[FeatureItem] | None = None) -> ArchitectureOutput:
    crew = Crew(
        agents=[architect],
        tasks=[build_architecture_task(requirements_text, features)],
        process=Process.sequential,
    )
    result = crew.kickoff()
    output = getattr(result, "pydantic", None)
    if output is None:
        raise RuntimeError("Architecture agent did not return a Pydantic output")
    return cast(ArchitectureOutput, output)


def run_implementation(requirements_text: str, architecture: ArchitectureOutput | None = None) -> ImplementationOutput:
    crew = Crew(
        agents=[developer],
        tasks=[build_implementation_task(requirements_text, architecture)],
        process=Process.sequential,
    )
    result = crew.kickoff()
    output = getattr(result, "pydantic", None)
    if output is None:
        raise RuntimeError("Developer agent did not return a Pydantic output")
    return cast(ImplementationOutput, output)


def run_qa(
    requirements_text: str,
    architecture: ArchitectureOutput | None = None,
    implementation: ImplementationOutput | None = None,
) -> QAOutput:
    crew = Crew(
        agents=[qa_tester],
        tasks=[build_qa_task(requirements_text, architecture, implementation)],
        process=Process.sequential,
    )
    result = crew.kickoff()
    output = getattr(result, "pydantic", None)
    if output is None:
        raise RuntimeError("QA agent did not return a Pydantic output")
    return cast(QAOutput, output)


def run_security_review(
    requirements_text: str,
    architecture: ArchitectureOutput | None = None,
    implementation: ImplementationOutput | None = None,
) -> SecurityReviewOutput:
    crew = Crew(
        agents=[security_reviewer],
        tasks=[build_security_review_task(requirements_text, architecture, implementation)],
        process=Process.sequential,
    )
    result = crew.kickoff()
    output = getattr(result, "pydantic", None)
    if output is None:
        raise RuntimeError("Security reviewer did not return a Pydantic output")
    return cast(SecurityReviewOutput, output)


def run_performance_review(
    requirements_text: str,
    architecture: ArchitectureOutput | None = None,
    implementation: ImplementationOutput | None = None,
) -> PerformanceReviewOutput:
    crew = Crew(
        agents=[performance_reviewer],
        tasks=[build_performance_review_task(requirements_text, architecture, implementation)],
        process=Process.sequential,
    )
    result = crew.kickoff()
    output = getattr(result, "pydantic", None)
    if output is None:
        raise RuntimeError("Performance reviewer did not return a Pydantic output")
    return cast(PerformanceReviewOutput, output)


def run_maintainability_review(
    requirements_text: str,
    architecture: ArchitectureOutput | None = None,
    implementation: ImplementationOutput | None = None,
) -> MaintainabilityReviewOutput:
    crew = Crew(
        agents=[maintainability_reviewer],
        tasks=[build_maintainability_review_task(requirements_text, architecture, implementation)],
        process=Process.sequential,
    )
    result = crew.kickoff()
    output = getattr(result, "pydantic", None)
    if output is None:
        raise RuntimeError("Maintainability reviewer did not return a Pydantic output")
    return cast(MaintainabilityReviewOutput, output)


def run_test_coverage_review(
    requirements_text: str,
    architecture: ArchitectureOutput | None = None,
    implementation: ImplementationOutput | None = None,
    qa_plan: QAOutput | None = None,
) -> TestCoverageReviewOutput:
    crew = Crew(
        agents=[test_coverage_reviewer],
        tasks=[build_test_coverage_review_task(requirements_text, architecture, implementation, qa_plan)],
        process=Process.sequential,
    )
    result = crew.kickoff()
    output = getattr(result, "pydantic", None)
    if output is None:
        raise RuntimeError("Test coverage reviewer did not return a Pydantic output")
    return cast(TestCoverageReviewOutput, output)
