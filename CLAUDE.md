# TesseractFlow Development Guidelines

**Last updated:** 2025-10-25 | **Current Feature:** 001-mvp-optimizer

## Project Overview

**TesseractFlow** is an LLM workflow optimization framework using Taguchi Design of Experiments. It helps developers systematically test multiple configuration variables (4-7) in just 8 experiments instead of 16, optimizing for quality, cost, and latency simultaneously.

**Current Status:** MVP Specification Complete ✅
**Branch:** `001-mvp-optimizer`
**Next:** Implementation (60-70 hours estimated)

## Active Technologies

- **Python 3.11+** - Core framework
- **LangGraph 0.2.0+** - Workflow orchestration
- **LiteLLM 1.0+** - Provider-agnostic LLM calls
- **Pydantic 2.0+** - Configuration validation
- **NumPy 1.24+** - Taguchi array math
- **SciPy 1.10+** - Statistical analysis
- **Matplotlib 3.7+** - Pareto visualization
- **PyYAML 6.0+** - Configuration parsing
- **Typer** - CLI framework
- **pytest 7.4+** - Testing (≥80% coverage for core)

## Project Structure

```text
tesseract_flow/
├── __init__.py
├── core/
│   ├── base_workflow.py       # BaseWorkflowService abstract class
│   ├── config.py              # Pydantic configs
│   └── strategies.py          # GenerationStrategy registry
├── experiments/
│   ├── taguchi.py             # L8 orthogonal array generator
│   ├── executor.py            # ExperimentExecutor
│   └── analysis.py            # MainEffectsAnalyzer
├── evaluation/
│   ├── rubric.py              # RubricEvaluator (LLM-as-judge)
│   └── metrics.py             # QualityScore, cost/latency tracking
├── optimization/
│   ├── utility.py             # UtilityFunction
│   └── pareto.py              # ParetoFrontier computation
├── cli/
│   ├── main.py                # CLI entry point (Typer)
│   ├── experiment.py          # experiment commands
│   └── visualize.py           # visualize commands
└── workflows/
    └── code_review.py         # Example workflow

specs/001-mvp-optimizer/       # Current feature specification
├── spec.md                    # User stories, requirements, success criteria
├── plan.md                    # Implementation plan, architecture
├── research.md                # Technical decisions (5 resolved unknowns)
├── data-model.md              # 10 entities with validation rules
├── tasks.md                   # 126 tasks across 6 phases
├── quickstart.md              # Complete user walkthrough
└── contracts/
    ├── cli-commands.md        # CLI command specifications
    └── core-apis.md           # Internal API contracts

tests/
├── unit/                      # Core algorithm tests (≥80% coverage)
├── integration/               # End-to-end workflow tests
└── fixtures/                  # Test data

examples/code_review/          # Example experiment configs
```

## Constitution Principles

**ALL development must uphold these 6 principles:**

1. **Workflows-as-Boundaries** - HITL occurs between workflows, not within them
2. **Generation Strategies as Variables** - Test prompting techniques experimentally (standard, CoT, few-shot, VS)
3. **Multi-Objective Optimization** - Always track Quality + Cost + Time
4. **Provider Agnostic** - Use LiteLLM for universal provider abstraction (no vendor lock-in)
5. **Transparency Over Automation** - Main effects analysis shows variable contributions
6. **Test-Driven Core** - Core algorithms require ≥80% test coverage

## Key Technical Decisions

**From research.md (Phase 0):**

1. **L8 Array:** Hard-coded NumPy constant (standard, fast, testable)
2. **Main Effects:** Taguchi formula with contribution percentages
3. **Pareto:** Sort-based O(n log n) algorithm (efficient, simple)
4. **CLI:** Typer (type-safe, Pydantic integration, async support)
5. **LLM-as-Judge:** Rubric + CoT prompting, temperature=0.3

## Common Commands

```bash
# Development
pytest                                  # Run all tests
pytest tests/unit -v                    # Run unit tests
pytest --cov=tesseract_flow            # Test with coverage
ruff check .                            # Lint code

# CLI Usage (after implementation)
tesseract experiment run config.yaml -o results.json
tesseract analyze results.json --show-chart
tesseract visualize pareto results.json -o pareto.png
```

## Implementation Status

**Phase 1: Setup** (T001-T007, 2-4 hours) - ⏳ Starting
**Phase 2: Foundation** (T008-T021, 6-8 hours) - 📋 Pending
**Phase 3: US1 - Run Experiment** (T022-T059, 16-20 hours) - 📋 Pending
**Phase 4: US2 - Analyze Results** (T060-T076, 10-12 hours) - 📋 Pending
**Phase 5: US3 - Visualize Pareto** (T077-T097, 8-10 hours) - 📋 Pending
**Phase 6: Polish** (T098-T124, 12-16 hours) - 📋 Pending

See `specs/001-mvp-optimizer/tasks.md` for complete task breakdown.

## Code Style

**Python 3.11+:**
- Follow PEP 8 conventions
- Use type hints (enforced by Pydantic where applicable)
- Docstrings for all public APIs
- Use Pydantic for all config/entity validation
- Async/await for LLM calls
- Test-driven development (write tests first)

## Performance Goals

- L8 experiment (8 tests) completes in <15 minutes
- Main effects analysis <5 seconds
- Pareto visualization <2 seconds

## MVP Constraints

- **CLI-only** (no web UI for MVP)
- **Sequential execution** (no parallelization for MVP)
- **JSON storage** (no database for MVP)
- **L8 array only** (defer L16/L18 to Phase 2)
- **Rubric evaluator only** (defer pairwise A/B to Phase 2)

## Recent Changes

- **2025-10-25**: MVP specification complete (spec.md, plan.md, tasks.md, quickstart.md)
- **2025-10-25**: Research phase complete (5 technical unknowns resolved)
- **2025-10-25**: Data model designed (10 entities)
- **2025-10-25**: API contracts defined (CLI + core APIs)
- **2025-10-25**: Constitution validation passed (all 6 principles upheld)
- **2025-10-25**: Branch `001-mvp-optimizer` created and pushed
- **2025-10-25**: Ready for implementation (Phase 1 starting)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
