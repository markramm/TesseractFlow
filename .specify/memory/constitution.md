<!--
Sync Impact Report:
- Version change: [NEW] → 1.0.0
- Created initial constitution for TesseractFlow
- Principles established: 6 core principles
- Templates: ✅ All initial templates in sync (no existing artifacts to update)
- Follow-up TODOs: None
-->

# TesseractFlow Constitution

## Core Principles

### I. Workflows-as-Boundaries (HITL Pattern)

Human-in-the-loop (HITL) MUST occur **between workflows**, not within them.

**Rules:**
- Workflows MUST complete synchronously (10-60 seconds target)
- Workflows MUST NOT implement pause/resume or checkpointing
- HITL approval MUST use database queue pattern (not in-workflow pausing)
- Complex orchestration tools (Temporal, Airflow) MUST NOT be required for basic workflows

**Rationale:** This eliminates 80% of infrastructure complexity while maintaining all HITL benefits. Workflows remain simple, testable, and framework-agnostic. Human reviews happen asynchronously via approval queue APIs.

### II. Generation Strategies as Experimental Variables

Prompting techniques (Verbalized Sampling, Chain-of-Thought, Few-Shot) MUST be treated as **experimental variables to test**, not as core framework features.

**Rules:**
- Framework MUST NOT have hard dependencies on specific generation strategies
- New strategies MUST be pluggable via registry pattern
- VS and other advanced strategies MUST be optional dependencies
- Experiments MUST test strategy effectiveness (not assume it)

**Rationale:** This keeps the framework general-purpose and prevents premature optimization. Data determines which strategies work, not hype. Users can add custom strategies without modifying core framework.

### III. Multi-Objective Optimization

All optimization MUST consider **Quality + Cost + Time** simultaneously, not quality alone.

**Rules:**
- Experiments MUST track quality score, cost (USD), and latency (ms) for every test
- Utility function MUST allow weighted combination of objectives
- Pareto frontier MUST be computed and visualized (Quality vs Cost)
- Users MUST be able to choose from Pareto-optimal configurations based on budget

**Rationale:** Real-world constraints include cost budgets and latency requirements. Single-objective optimization ignores business reality. Pareto frontiers show trade-offs explicitly.

### IV. Provider Agnostic

Framework MUST work with any LLM provider, not lock users into specific vendors.

**Rules:**
- Provider abstraction layer MUST be used (LiteLLM or equivalent)
- Workflows MUST NOT contain provider-specific code
- Configuration MUST support provider fallbacks
- Experiments MUST be able to test provider variance as a variable

**Rationale:** Fine-tuning locks users to specific models/versions. TesseractFlow optimizes workflows, not weights, enabling continuous optimization as models evolve. Provider flexibility is core to the value proposition.

### V. Transparency Over Automation

Framework MUST make optimization transparent and explainable, not opaque.

**Rules:**
- Main effects analysis MUST show which variables contribute to quality
- Taguchi arrays MUST be documented with rationale for experiment count
- Optimal configuration MUST be accompanied by contribution percentages
- Users MUST be able to override automated recommendations with data-backed reasoning

**Rationale:** Unlike DSPy's auto-optimization, TesseractFlow shows users *why* configurations work. This builds trust and enables informed decision-making. Scientists need explainability, not black boxes.

### VI. Test-Driven Core

Core optimization algorithms (Taguchi, main effects, Pareto) MUST have comprehensive test coverage.

**Rules:**
- Taguchi array generation MUST have unit tests verifying orthogonality
- Main effects calculation MUST have tests with known expected outputs
- Pareto frontier computation MUST have tests for edge cases
- Test coverage for core modules MUST be ≥80%

**Rationale:** Users trust the framework to guide expensive optimization decisions. Buggy core algorithms would produce incorrect recommendations, wasting time and money. Core math MUST be rock-solid.

## Technology Stack Requirements

### Mandatory Technologies

- **Python 3.11+**: Required for VS integration, type hints, and modern syntax
- **LangGraph**: Required for workflow orchestration (simple, synchronous)
- **LiteLLM**: Required for provider abstraction
- **FastAPI**: Required for REST API endpoints (approval queue, experiments)
- **PostgreSQL**: Required for persistence (workflows, results, approvals)
- **Pydantic**: Required for configuration validation and type safety

### Optional Technologies

- **Verbalized Sampling**: Optional strategy (separate install)
- **Langfuse/Weave**: Optional observability integrations
- **TruLens**: Optional evaluator wrappers

### Prohibited Technologies

- **Temporal**: Too complex for workflows-as-boundaries pattern
- **AI SDK 6**: TypeScript incompatible with Python VS library
- **Celery**: Task queue only, no workflow orchestration needed

**Rationale:** Mandatory technologies support core principles (provider agnostic, testable, HITL-friendly). Optional technologies enhance but don't constrain. Prohibited technologies violate architectural principles or add unnecessary complexity.

## Development Workflow

### Experiment-Driven Development

New features MUST follow this workflow:

1. **Define hypothesis**: What variable are we testing? What's the expected impact?
2. **Design experiment**: Taguchi array, variable levels, test cases
3. **Implement feature**: Build the workflow or strategy
4. **Run experiment**: Execute tests, collect metrics
5. **Analyze results**: Main effects, Pareto frontier, optimal config
6. **Document findings**: Which variables matter? Contribution percentages?

**Rationale:** TesseractFlow is a scientific tool. Feature development should model the scientific method we're enabling for users. "Measure twice, cut once."

### Code Review Requirements

**All PRs MUST:**
- Include tests for new functionality (no test = no merge)
- Update documentation if API changes
- Pass linting (Black, Ruff) and type checking (MyPy)
- Include performance impact analysis for core algorithms
- Reference GitHub issue or feature specification

**Review checklist:**
- [ ] Does this follow workflows-as-boundaries pattern?
- [ ] Are generation strategies pluggable?
- [ ] Is multi-objective optimization preserved?
- [ ] Is provider abstraction maintained?
- [ ] Are results transparent/explainable?
- [ ] Are core algorithms tested?

## Governance

### Amendment Procedure

Constitution amendments REQUIRE:
1. GitHub issue proposing the change with rationale
2. Discussion period (minimum 7 days)
3. Documented impact on existing code/users
4. Approval from project maintainers
5. Version bump following semantic versioning

### Version Semantics

- **MAJOR**: Backward-incompatible principle changes (e.g., removing provider agnosticism)
- **MINOR**: New principle added or existing principle materially expanded
- **PATCH**: Clarifications, typo fixes, non-semantic refinements

### Compliance

All code changes MUST be reviewed for constitution compliance before merge. When principles conflict with implementation convenience, **principles win**. Complexity must be justified against constitution principles.

Use `docs/architecture/` for detailed technical guidance that complements this constitution.

**Version**: 1.0.0 | **Ratified**: 2025-10-25 | **Last Amended**: 2025-10-25
