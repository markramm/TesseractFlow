# Implementation Plan: LLM Workflow Optimizer MVP

**Branch**: `001-mvp-optimizer` | **Date**: 2025-10-25 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-mvp-optimizer/spec.md`

## Summary

Build a Python-based LLM workflow optimization framework using Taguchi Design of Experiments (L8 array) that systematically tests multiple configuration variables (4-7) in 8 experiments instead of 16. The MVP includes core Taguchi array generation, rubric-based quality evaluation, multi-objective utility function (quality/cost/time), Pareto frontier visualization, and a complete code review workflow example. This establishes the foundation for "Lean AI Development" methodology and demonstrates 50% reduction in experiment count while optimizing for quality, cost, and latency simultaneously.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**:
- LiteLLM 1.0+ (provider-agnostic LLM calls)
- LangGraph 0.2.0+ (workflow orchestration)
- Pydantic 2.0+ (configuration validation)
- NumPy 1.24+ (Taguchi array math)
- SciPy 1.10+ (statistical analysis)
- Matplotlib 3.7+ (Pareto visualization)
- PyYAML 6.0+ (configuration parsing)

**Storage**: JSON files (no database for MVP)
**Testing**: pytest 7.4+ with pytest-asyncio 0.21+
**Target Platform**: Linux/macOS command-line (developers)
**Project Type**: Single Python package with CLI
**Performance Goals**:
- L8 experiment (8 tests) completes in <15 minutes
- Main effects analysis <5 seconds
- Pareto visualization <2 seconds

**Constraints**:
- CLI-only (no web UI)
- Sequential experiment execution (no parallelization for MVP)
- Provider API rate limits (handle with exponential backoff)

**Scale/Scope**:
- 4-7 variables per experiment
- 8 test configurations (L8 array)
- Code review workflow with ~100-500 lines of code per test

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ Constitution Compliance

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Workflows-as-Boundaries** | ✅ PASS | MVP has no HITL (future feature). Workflows complete synchronously. |
| **II. Generation Strategies as Variables** | ✅ PASS | Strategies are pluggable via registry pattern. No hard VS dependency. |
| **III. Multi-Objective Optimization** | ✅ PASS | Tracks quality, cost, time. Utility function allows weighting. Pareto frontier computed. |
| **IV. Provider Agnostic** | ✅ PASS | Uses LiteLLM for provider abstraction. No vendor lock-in. |
| **V. Transparency Over Automation** | ✅ PASS | Main effects analysis shows variable contributions. Taguchi arrays documented. |
| **VI. Test-Driven Core** | ✅ PASS | Core algorithms (Taguchi, main effects, Pareto) will have ≥80% test coverage. |

**Mandatory Technologies**: All required technologies are included (Python 3.11+, LangGraph, LiteLLM, FastAPI for future, PostgreSQL for future, Pydantic)

**Optional Technologies**: Verbalized Sampling (optional), Langfuse/Weave (future)

**Prohibited Technologies**: None used (no Temporal, no AI SDK 6, no premature Celery)

### Post-Design Re-Check (Phase 1)

*To be completed after data-model.md and contracts/ are generated*

## Project Structure

### Documentation (this feature)

```text
specs/001-mvp-optimizer/
├── plan.md              # This file (/speckit.plan output)
├── research.md          # Phase 0 output (technical decisions)
├── data-model.md        # Phase 1 output (entities/relationships)
├── quickstart.md        # Phase 1 output (test scenarios)
├── contracts/           # Phase 1 output (CLI commands, internal APIs)
│   ├── cli-commands.md
│   └── core-apis.md
└── checklists/
    └── requirements.md  # Already created
```

### Source Code (repository root)

```text
tesseract_flow/
├── __init__.py                    # Package exports
├── core/
│   ├── __init__.py
│   ├── base_workflow.py           # BaseWorkflowService abstract class
│   ├── config.py                  # WorkflowConfig, ExperimentConfig (Pydantic)
│   └── strategies.py              # GenerationStrategy registry
├── experiments/
│   ├── __init__.py
│   ├── taguchi.py                 # L8 orthogonal array generator
│   ├── executor.py                # ExperimentExecutor (runs tests)
│   └── analysis.py                # MainEffectsAnalyzer
├── evaluation/
│   ├── __init__.py
│   ├── rubric.py                  # RubricEvaluator (LLM-as-judge)
│   └── metrics.py                 # QualityScore, cost/latency tracking
├── optimization/
│   ├── __init__.py
│   ├── utility.py                 # UtilityFunction (weighted quality/cost/time)
│   └── pareto.py                  # ParetoFrontier computation & visualization
├── cli/
│   ├── __init__.py
│   ├── main.py                    # CLI entry point (Click/Typer)
│   ├── experiment.py              # experiment run/analyze commands
│   └── visualize.py               # visualize pareto command
└── workflows/
    ├── __init__.py
    └── code_review.py             # CodeReviewWorkflow example

examples/
├── code_review/
│   ├── experiment_config.yaml     # Example L8 experiment config
│   ├── workflow_config.yaml       # CodeReview workflow config
│   └── sample_code/               # Test code samples
│       ├── example1.py
│       └── example2.py
└── README.md                      # How to run examples

tests/
├── unit/
│   ├── test_taguchi.py            # L8 array generation tests
│   ├── test_main_effects.py       # Main effects calculation tests
│   ├── test_pareto.py             # Pareto frontier tests
│   ├── test_utility.py            # Utility function tests
│   └── test_config.py             # Config validation tests
├── integration/
│   ├── test_experiment_flow.py    # End-to-end experiment execution
│   └── test_code_review.py        # Code review workflow tests
└── fixtures/
    ├── experiment_results.json    # Known good results for testing
    └── test_configs.yaml          # Test configurations

docs/
├── architecture/                  # Existing architecture docs
│   ├── unified-spec.md
│   ├── simplified-hitl.md
│   └── generation-strategies.md
├── user-guide/                    # New user documentation
│   ├── quickstart.md
│   ├── configuration.md
│   └── interpreting-results.md
└── api/                           # API documentation
    └── core-modules.md

pyproject.toml                     # Already exists
README.md                          # Already exists
.specify/                          # Speckit tooling
specs/                             # Feature specifications
```

**Structure Decision**: Single Python package structure chosen because:
- MVP is a library/CLI tool (no separate frontend/backend)
- All code in Python (no multi-language concerns)
- Clear separation: core logic, experiments, evaluation, optimization, CLI, workflows
- Examples directory shows usage patterns
- Test structure mirrors source structure

## Complexity Tracking

> No constitution violations - this section is empty.

---

## Phase 0: Research & Decisions

### Research Tasks

The following unknowns need resolution before detailed design:

1. **Taguchi L8 Array Implementation**
   - **Question**: What's the canonical L8 orthogonal array for 4-7 variables?
   - **Decision needed**: Matrix representation, validation approach
   - **Research**: Find standard L8 array, verify orthogonality properties

2. **Main Effects Calculation**
   - **Question**: How to compute main effects from Taguchi results?
   - **Decision needed**: Formula for effect size, contribution percentage
   - **Research**: Taguchi DOE textbooks, industrial examples

3. **Pareto Frontier Algorithm**
   - **Question**: Most efficient algorithm for 2D Pareto frontier?
   - **Decision needed**: Complexity, library vs custom implementation
   - **Research**: Computational geometry libraries, NumPy/SciPy options

4. **CLI Framework**
   - **Question**: Click vs Typer for modern Python CLI?
   - **Decision needed**: Which provides better type safety, async support
   - **Research**: Compare developer experience, async support, Pydantic integration

5. **LLM-as-Judge Best Practices**
   - **Question**: How to minimize bias in rubric-based evaluation?
   - **Decision needed**: Temperature, model choice, prompt structure
   - **Research**: Recent papers on LLM evaluation, bias mitigation techniques

---

## Phase 1: Design

*To be generated: data-model.md, contracts/, quickstart.md*

### Data Model Preview

Key entities (detailed in data-model.md):
- **ExperimentConfig**: Variables, levels, utility weights, workflow reference
- **TestConfiguration**: Specific variable values for one test run
- **ExperimentResult**: Collection of test results, metadata
- **TestResult**: Quality score, cost, latency, workflow output
- **MainEffects**: Variable contributions, effect sizes
- **ParetoPoint**: Configuration on frontier, dominance relationships

### API Contracts Preview

CLI commands (detailed in contracts/cli-commands.md):
- `tesseract experiment run <config.yaml>`
- `tesseract analyze <results.json>`
- `tesseract visualize pareto <results.json>`

Internal APIs (detailed in contracts/core-apis.md):
- `TaguchiGenerator.generate_l8_array(num_variables)`
- `ExperimentExecutor.run(experiment_config)`
- `MainEffectsAnalyzer.compute(results)`
- `ParetoFrontier.compute(results, x_axis, y_axis)`

### Test Scenarios Preview

Quickstart test cases (detailed in quickstart.md):
1. Run simple 4-variable code review experiment
2. Analyze results to identify optimal config
3. Generate Pareto chart showing trade-offs
4. Export and deploy optimal configuration

---

## Phase 2: Task Generation

*To be generated by `/speckit.tasks` command (not part of this plan)*

The tasks.md will break down implementation into:
- **Phase 1: Setup** - Project structure, dependencies
- **Phase 2: Core Taguchi** - L8 array generation, config validation
- **Phase 3: Experiment Execution** - Executor, progress tracking
- **Phase 4: Evaluation** - Rubric evaluator, metrics
- **Phase 5: Analysis** - Main effects, utility function
- **Phase 6: Visualization** - Pareto frontier, charts
- **Phase 7: Code Review Example** - Complete workflow
- **Phase 8: CLI** - Command interface
- **Phase 9: Documentation** - User guide, API docs
- **Phase 10: Polish** - Error handling, logging, packaging

---

## Implementation Strategy

### MVP-First Approach

**Week 1-2: Core Taguchi**
- L8 array generator
- Config validation
- Basic experiment executor

**Week 3-4: Evaluation**
- Rubric evaluator
- Cost/latency tracking
- Main effects analysis

**Week 5-6: Optimization**
- Utility function
- Pareto frontier computation
- Visualization

**Week 7-8: Example & CLI**
- Code review workflow
- CLI commands
- End-to-end testing

**Week 9-10: Documentation & Polish**
- User guide
- Example scenarios
- Error handling refinement

### Success Gates

After each phase, validate:
1. Unit tests pass (≥80% coverage for core)
2. Constitution principles upheld
3. Integration test demonstrates end-to-end flow
4. Performance targets met (15min experiment, 5s analysis, 2s viz)

### Risk Mitigation

- **Risk**: LLM-as-judge unreliable → **Mitigation**: Test with multiple rubrics, allow human review override
- **Risk**: API rate limits → **Mitigation**: Exponential backoff, provider rotation
- **Risk**: Taguchi math errors → **Mitigation**: Comprehensive unit tests with known results
- **Risk**: Scope creep → **Mitigation**: Strict MVP boundaries, defer HITL/database/API

---

## Post-Phase-0 Notes

**✅ Research Completed - 2025-10-25**

All 5 research questions resolved. Key decisions:

1. **L8 Array:** Hard-coded NumPy constant (standard, fast, testable)
2. **Main Effects:** Standard Taguchi formula with contribution percentages
3. **Pareto:** Sort-based O(n log n) algorithm (efficient, simple)
4. **CLI:** Typer (type-safe, Pydantic integration, async support)
5. **LLM-as-Judge:** Rubric + CoT, temperature=0.3 (research-backed)

No blocking unknowns remain. Ready for Phase 1 design.

## Post-Phase-1 Notes

**✅ Design Completed - 2025-10-25**

Artifacts generated:
- ✅ `data-model.md` - 10 entities with relationships, validation rules
- ✅ `contracts/cli-commands.md` - 4 CLI commands fully specified
- ✅ `contracts/core-apis.md` - 6 modules with API contracts
- ✅ `quickstart.md` - Complete walkthrough with example

**Constitution Re-Check:**
- ✅ All 6 principles upheld
- ✅ No violations introduced during design
- ✅ Mandatory technologies aligned
- ✅ No prohibited technologies used

**Key Design Decisions:**
- JSON file storage (no database for MVP)
- Typer CLI with Rich progress bars
- Pydantic for all config/entity validation
- Provider-agnostic via LiteLLM
- Test coverage ≥80% for core algorithms

**Ready for:** `/speckit.tasks` to generate implementation breakdown
