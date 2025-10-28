# TesseractFlow Development Guidelines

**Last updated:** 2025-10-26 | **Current Feature:** 002-web-ui-api

## Project Overview

**TesseractFlow** is an LLM workflow optimization framework using Taguchi Design of Experiments. It helps developers systematically test multiple configuration variables (4-7) in just 8 experiments instead of 16, optimizing for quality, cost, and latency simultaneously.

**Current Status:** v0.1.1 Released ✅ | v0.2 Planning Complete ✅
**Branch:** `main`
**Next:** v0.2 Implementation - Web UI + API (120-150 hours estimated)

## Active Technologies

### Core Framework (v0.1)
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

### Web UI + API (v0.2, Planned)
- **FastAPI 0.109+** - Async REST API framework
- **Uvicorn 0.27+** - ASGI server
- **Streamlit 1.30+** - Web UI framework
- **SQLAlchemy 2.0+** - ORM and database layer
- **Alembic 1.13+** - Database migrations
- **python-jose 3.3+** - JWT authentication
- **passlib 1.7+** - Password hashing
- **cryptography 41.0+** - API key encryption

## Project Structure

```text
tesseract_flow/
├── __init__.py
├── core/                      # Core framework (v0.1)
│   ├── base_workflow.py       # BaseWorkflowService abstract class
│   ├── config.py              # Pydantic configs
│   └── strategies.py          # GenerationStrategy registry
├── experiments/               # Experiment execution (v0.1)
│   ├── taguchi.py             # L8 orthogonal array generator
│   ├── executor.py            # ExperimentExecutor
│   └── analysis.py            # MainEffectsAnalyzer
├── evaluation/                # Quality evaluation (v0.1)
│   ├── rubric.py              # RubricEvaluator (LLM-as-judge)
│   └── metrics.py             # QualityScore, cost/latency tracking
├── optimization/              # Multi-objective optimization (v0.1)
│   ├── utility.py             # UtilityFunction
│   └── pareto.py              # ParetoFrontier computation
├── cli/                       # Command-line interface (v0.1)
│   ├── main.py                # CLI entry point (Typer)
│   ├── experiment.py          # experiment commands
│   └── visualize.py           # visualize commands
├── api/                       # REST API (v0.2, Planned)
│   ├── main.py                # FastAPI app
│   ├── routes/                # API endpoints
│   ├── models/                # SQLAlchemy models
│   ├── schemas/               # Pydantic request/response
│   └── database.py            # Database connection
├── ui/                        # Web UI (v0.2, Planned)
│   ├── app.py                 # Streamlit app
│   ├── pages/                 # Multi-page app
│   └── components/            # Reusable UI components
└── workflows/                 # Example workflows (v0.1)
    └── code_review.py         # Code review workflow

specs/
├── 001-mvp-optimizer/         # v0.1 specification (Complete)
│   ├── spec.md                # User stories, requirements
│   ├── plan.md                # Implementation plan
│   ├── research.md            # Technical decisions
│   ├── data-model.md          # Data entities
│   ├── tasks.md               # Task breakdown
│   └── quickstart.md          # User walkthrough
└── 002-web-ui-api/            # v0.2 specification (Planning)
    ├── spec.md                # User stories (6 stories)
    └── plan.md                # Implementation plan (6 weeks)

tests/
├── unit/                      # Core algorithm tests (≥80% coverage)
├── integration/               # End-to-end workflow tests
├── api/                       # API endpoint tests (v0.2)
└── ui/                        # UI component tests (v0.2)

examples/code_review/          # Example experiment configs
docs/                          # Strategy and research docs
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

# CLI Usage (v0.1)
tesseract experiment run config.yaml -o results.json
tesseract analyze main-effects results.json
tesseract visualize pareto results.json -o pareto.png

# Web UI + API (v0.2, Planned)
tesseract serve                         # Start API + UI
# API: http://localhost:8000
# UI: http://localhost:8501
# Docs: http://localhost:8000/docs
```

## Implementation Status

### v0.1 CLI (Released ✅)
- **Status:** Complete and released (v0.1.1 on 2025-10-26)
- **Features:** L8 experiments, main effects, Pareto frontier, resume support, caching
- **Docs:** `specs/001-mvp-optimizer/`

### v0.2 Web UI + API (Planning Complete ✅)
- **Status:** Specification and planning complete, ready for implementation
- **Est. Duration:** 6 weeks (120-150 hours)
- **Docs:** `specs/002-web-ui-api/`

**Phases:**
1. **Backend Foundation** (Week 1-2, 30-40 hours) - FastAPI, SQLAlchemy, WebSocket
2. **Web UI** (Week 3-4, 40-50 hours) - Streamlit, dashboards, knowledge base
3. **Authentication** (Week 5, 20-25 hours) - User accounts, JWT, API key storage
4. **Polish & Testing** (Week 6, 30-35 hours) - Error handling, E2E tests, docs

**Target Release:** December 2025

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

## Version Roadmap

### v0.1 (Released) - CLI Foundation
- ✅ L8 orthogonal arrays
- ✅ Main effects analysis
- ✅ Pareto frontier visualization
- ✅ Resume support
- ✅ Evaluation caching
- ✅ CLI with Typer

**Constraints:** CLI-only, sequential execution, JSON storage

### v0.2 (Planning) - Web UI + API
- 🔄 FastAPI REST API
- 🔄 Streamlit web UI
- 🔄 User authentication (JWT)
- 🔄 SQLite database
- 🔄 Knowledge base explorer
- 🔄 Real-time progress (WebSocket)

**Target:** December 2025

### v0.3 (Future) - Scale & Collaboration
- Team workspaces
- PostgreSQL migration
- Parallel execution
- L16/L18 arrays
- Experiment comparison
- React migration (if needed)

### v1.0 (Future) - SaaS & Enterprise
- Hosted SaaS platform
- Enterprise SSO
- CI/CD integrations
- Workflow marketplace
- Advanced evaluators

## Recent Changes

- **2025-10-28**: Reasoning & Verbalized Sampling mixins added (Wave 4 experiments)
- **2025-10-28**: GPT-5 Mini evaluator testing completed (16.67% clustering, 55% reduction)
- **2025-10-28**: Structured fiction rubric implemented (4 technical dimensions)
- **2025-10-28**: Evaluator comparison docs created (docs/evaluator_comparison_gpt5mini.md)
- **2025-10-26**: v0.2 specification complete (Web UI + API planning)
- **2025-10-26**: Implementation plan created (6 weeks, 120-150 hours)
- **2025-10-26**: Strategic conversation summary documented
- **2025-10-26**: DSPy integration research completed
- **2025-10-26**: Iteration patterns guide created
- **2025-10-26**: v0.1.1 released (pytest + resume fixes)
- **2025-10-26**: v0.1.0 released (initial CLI release)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
