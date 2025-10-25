# Feature Specification: LLM Workflow Optimizer MVP

**Feature Branch**: `001-mvp-optimizer`
**Created**: 2025-10-25
**Status**: Draft
**Input**: User description: "Build an LLM workflow optimization framework that uses Taguchi Design of Experiments to systematically optimize LLM workflows. MVP includes L8 orthogonal array generator, basic rubric-based evaluator, multi-objective utility function, Pareto frontier visualization, main effects analysis, and code review workflow example."

## Overview

This MVP delivers a systematic LLM workflow optimization framework using Taguchi Design of Experiments. Unlike ad-hoc prompt testing or expensive fine-tuning, this framework enables users to test multiple configuration variables efficiently (4 variables in 8 experiments instead of 16) and optimize for quality, cost, and latency simultaneously.

The MVP focuses on proving the methodology works with a complete code review workflow example, establishing the foundation for the broader "Lean AI Development" toolkit.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run Taguchi Experiment (Priority: P1)

An AI engineer wants to systematically optimize their code review LLM workflow by testing different configurations (temperature, model, context size, generation strategy) to find the best quality/cost/latency trade-off.

**Why this priority**: This is the core value proposition - systematic experimentation using Taguchi DOE. Without this, the framework has no purpose. This story alone delivers demonstrable value.

**Independent Test**: Can be fully tested by defining 4 variables, running 8 experiments, and receiving results with quality scores, costs, and latencies for each test configuration. Delivers immediate value by identifying which variables matter most.

**Acceptance Scenarios**:

1. **Given** a YAML configuration file with 4 variables (each with 2 levels), **When** user runs `tesseract experiment run config.yaml`, **Then** system generates L8 Taguchi array (8 test configurations) and executes all experiments
2. **Given** experiments are running, **When** user checks progress, **Then** system shows current test number, configuration being tested, and preliminary results
3. **Given** all 8 experiments complete, **When** user views results, **Then** system displays quality score, cost, and latency for each configuration
4. **Given** experiment results, **When** user requests main effects analysis, **Then** system shows contribution percentage for each variable

---

### User Story 2 - Analyze Results & Identify Optimal Config (Priority: P2)

An AI engineer wants to understand which configuration variables contribute most to quality and identify the optimal configuration to deploy.

**Why this priority**: Results analysis is essential to make the experiments actionable. Without analysis, users just have raw data. This transforms data into decisions.

**Independent Test**: Can be tested by loading completed experiment results and running analysis commands. Delivers value by showing which variables to focus on and what configuration to use.

**Acceptance Scenarios**:

1. **Given** completed experiment results, **When** user runs `tesseract analyze results.json`, **Then** system displays main effects showing each variable's contribution percentage
2. **Given** main effects analysis, **When** user requests optimal configuration, **Then** system identifies configuration with highest utility score and shows the settings
3. **Given** optimal configuration identified, **When** user exports configuration, **Then** system generates deployable YAML config file
4. **Given** experiment results, **When** user compares two configurations, **Then** system highlights differences and shows quality/cost/latency delta

---

### User Story 3 - Visualize Quality/Cost Trade-offs (Priority: P3)

An AI engineer wants to see the Pareto frontier showing quality vs cost trade-offs to choose a configuration that fits their budget constraints.

**Why this priority**: Pareto visualization helps users make informed trade-off decisions when optimal config exceeds budget. Adds polish and decision-support to core functionality.

**Independent Test**: Can be tested by loading experiment results and generating Pareto chart. Delivers value by making trade-offs visually obvious and enabling budget-constrained decisions.

**Acceptance Scenarios**:

1. **Given** completed experiment results, **When** user runs `tesseract visualize pareto results.json`, **Then** system generates scatter plot with cost on X-axis, quality on Y-axis, and bubble size showing latency
2. **Given** Pareto frontier chart, **When** user views plot, **Then** Pareto-optimal configurations are highlighted (not dominated by any other configuration)
3. **Given** Pareto chart with multiple optimal points, **When** user selects a cost threshold, **Then** system shows best quality configuration within budget
4. **Given** Pareto visualization, **When** user saves chart, **Then** system exports publication-quality SVG/PNG with clear axis labels and legend

---

### Edge Cases

- What happens when experiment fails mid-execution? System must save partial results and allow resuming from last completed test
- What happens when two variables have identical contribution? System must report both equally and note low differentiation
- What happens when user defines <4 or >7 variables? System must validate L8 supports 4-7 variables and reject invalid configs
- What happens when all configurations score identically? System must detect this and warn user that variables may not matter for this workflow
- What happens when LLM API returns errors? System must retry with exponential backoff and log failures without crashing experiment

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST generate L8 Taguchi orthogonal array from 4-7 variable definitions
- **FR-002**: System MUST accept YAML configuration specifying variables with 2 levels each
- **FR-003**: System MUST execute experiments sequentially with each test configuration
- **FR-004**: System MUST evaluate workflow outputs using rubric-based quality scoring
- **FR-005**: System MUST track quality score (0-1), cost (USD), and latency (ms) for each experiment
- **FR-006**: System MUST compute main effects showing each variable's contribution to utility
- **FR-007**: System MUST calculate utility function as weighted combination: w_quality × quality - w_cost × norm_cost - w_time × norm_time, where normalization uses min-max scaling across the current experiment's 8 trials (norm_x = (x - min_x) / (max_x - min_x), or 0.0 if max == min)
- **FR-008**: System MUST identify Pareto frontier (non-dominated configurations on quality vs cost)
- **FR-009**: System MUST generate Pareto visualization as SVG/PNG scatter plot
- **FR-010**: System MUST save experiment results as JSON including all configs, scores, costs, latencies
- **FR-011**: System MUST provide code review workflow as working example
- **FR-012**: System MUST allow users to specify custom utility weights (quality/cost/time)
- **FR-013**: System MUST validate that variable count is between 4-7 for L8 array
- **FR-014**: System MUST provide progress updates during experiment execution
- **FR-015**: System MUST support best-effort reproducibility by: (1) version-controlling configuration files, (2) ensuring deterministic workflow logic, (3) optionally caching LLM responses for test replay, (4) documenting non-determinism sources (LLM API sampling, rate limits) in experiment metadata

### Non-Functional Requirements

- **NFR-001**: Complete L8 experiment (8 tests) MUST finish in under 15 minutes with mock provider, or under 30 minutes with real LLM providers (accounting for API rate limits and retries)
- **NFR-002**: Main effects analysis MUST complete in under 5 seconds
- **NFR-003**: Pareto visualization generation MUST complete in under 2 seconds
- **NFR-004**: Experiment configuration YAML MUST be validated with clear error messages
- **NFR-005**: All core algorithms (Taguchi array, main effects, Pareto) MUST have unit test coverage ≥80%

### Key Entities

- **Experiment**: Represents a Taguchi DOE run with variables, test configurations, and results. Contains experiment metadata, variable definitions, generated test configs, and execution status.
- **Variable**: A parameter to optimize with name, level_1 value, and level_2 value (e.g., temperature: {1: 0.3, 2: 0.7})
- **TestConfiguration**: One specific combination of variable values from the Taguchi array (e.g., {temp: 0.7, model: "claude", context: "full", strategy: "standard"})
- **TestResult**: Output from running one test configuration including quality score, cost, latency, and raw workflow output
- **QualityScore**: Evaluation result with dimension scores (clarity, depth, etc.), overall score, and metadata
- **MainEffects**: Analysis showing each variable's average utility at level 1 vs level 2, effect size, and contribution percentage
- **ParetoPoint**: Configuration on the Pareto frontier with quality, cost, latency, and dominated/dominating relationships

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: User can define 4 variables and run complete L8 experiment in under 15 minutes (mock provider) or 30 minutes (real LLM provider)
- **SC-002**: System correctly identifies which variable contributes most to quality (verifiable by known test case)
- **SC-003**: Pareto frontier identifies at least 3 non-dominated configurations for code review example
- **SC-004**: Optimal configuration improves quality by 10-30% vs random baseline configuration
- **SC-005**: User can reproduce experiment configuration and workflow logic deterministically; LLM response caching enables exact result replay for testing (best-effort reproducibility given inherent LLM API stochasticity)
- **SC-006**: Main effects analysis shows clear variable rankings (contribution % sum to ~100%)
- **SC-007**: Generated Pareto chart clearly shows quality/cost trade-off with labeled axes
- **SC-008**: Code review example demonstrates complete workflow from config to deployment

### Assumptions

- Users have basic understanding of experimental design concepts (variables, levels)
- Users can write YAML configuration files
- LLM API providers respond within reasonable timeouts (30s per call)
- Code review tasks are representative of typical LLM workflow optimization needs
- Quality evaluation via LLM-as-judge is sufficiently reliable for MVP validation
- Users have API keys for at least one LLM provider (OpenRouter, Anthropic, or OpenAI)

### Dependencies

**Primary Dependencies:**
- Python 3.11+ - Core language
- LangGraph 0.2.0+ - Workflow orchestration (mandatory)
- LiteLLM 1.0+ - Provider-agnostic LLM calls
- Pydantic 2.0+ - Configuration validation
- NumPy 1.24+ - Taguchi array math
- SciPy 1.10+ - Statistical analysis
- Matplotlib 3.7+ - Pareto visualization
- PyYAML 6.0+ - Configuration parsing
- Typer 0.9+ - CLI framework
- Rich 13.0+ - Terminal UI (progress bars, tables)
- pytest 7.4+ - Testing framework

### Out of Scope (MVP)

- HITL approval queue (future feature)
- Database persistence (JSON files sufficient for MVP)
- REST API (CLI only for MVP)
- L16/L18 orthogonal arrays (L8 sufficient to prove methodology)
- Advanced evaluators (pairwise, ensemble) - basic rubric evaluator only
- Verbalized Sampling integration (will test as experimental variable in examples)
- Web UI (command-line interface only)
- Multi-user support
- Experiment history/comparison across runs
