# Changelog

All notable changes to TesseractFlow will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2025-10-26

### Fixed

- **pytest dependency issue** - Removed `--cov` options from default pytest config in pyproject.toml. Coverage reporting now requires explicit `pytest --cov` invocation with `pytest-cov` from dev extras. This fixes the "unrecognized arguments" error when running `pytest` after fresh install with `pip install -e .` ([tesseract_flow/experiments/executor.py:126-131](https://github.com/markramm/TesseractFlow/blob/main/tesseract_flow/experiments/executor.py#L126-L131))

- **--resume crash on completed experiments** - Fixed `ValueError` when using `--resume` flag on an already-completed experiment. Executor now checks if experiment status is COMPLETED before attempting to call `mark_completed()`, preventing invalid state transition error ([tesseract_flow/experiments/executor.py:126-131](https://github.com/markramm/TesseractFlow/blob/main/tesseract_flow/experiments/executor.py#L126-L131))

### Changed

- pytest coverage reporting is now opt-in: run `pytest --cov=tesseract_flow --cov-report=html` for coverage analysis

### Developer Notes

Both issues were discovered during beta testing with fresh developer installations. Thanks to early testers for the detailed bug reports!

---

## [0.1.0] - 2025-10-26

### Added - Core Framework

- **Taguchi L8 Orthogonal Arrays** - Efficient experimental design testing 4 variables in 8 experiments instead of 16
- **Multi-Objective Optimization** - Utility function balancing quality, cost, and latency with configurable weights
- **LLM-as-Judge Evaluation** - Rubric-based quality scoring with customizable 0-100 point scale dimensions
- **Main Effects Analysis** - Statistical analysis showing variable contributions with percentages
- **Pareto Frontier Visualization** - Matplotlib charts highlighting quality vs cost trade-offs
- **Provider-Agnostic Architecture** - LiteLLM integration supporting 400+ models from any provider
- **Evaluation Caching** - Persistent cache for LLM evaluations to reduce redundant API calls
- **Resume Support** - Continue interrupted experiments from last checkpoint

### Added - CLI

- **Rich Terminal UI** - Beautiful progress bars, colored output, and formatted tables using Rich library
- `tesseract experiment run` - Execute L8 experiments with dry-run, resume, caching options
- `tesseract experiment validate` - Validate configuration files before running
- `tesseract experiment status` - Check experiment progress and resume hints
- `tesseract analyze main-effects` - Compute variable contributions and identify optimal configuration
- `tesseract analyze summary` - Quick overview of experiment results
- `tesseract visualize pareto` - Generate Pareto frontier charts with budget filtering
- `--log-level` - Global log level control (critical, error, warning, info, debug)
- `--version` - Display TesseractFlow version

### Added - Documentation

- **Comprehensive README** - Installation, quick start, CLI reference, examples, and use cases
- **OpenRouter Model Costs** (`docs/openrouter-model-costs.md`) - Pricing data for 15+ models across 6 cost tiers
- **OpenRouter Model Capabilities** (`docs/openrouter-model-capabilities.md`) - Performance benchmarks, optimal settings, decision trees
- **Project Evaluation** (`PROJECT_EVALUATION.md`) - Technical architecture, UX, product-market fit assessment (4.55/5)
- **Experiment Findings** (`experiments/FINDINGS.md`) - Real-world code review experiment results and insights
- **Example Configurations** - Production-grade YAML configs in `examples/code_review/`

### Added - Claude Code Integration

- **Experiment Designer Skill** (`.claude/skills/tesseract-experiment-designer/`) - AI-powered experiment design assistant
  - 5-step design process (requirements → recommendation → L8 design → cost estimation → config generation)
  - References model costs and capabilities documentation
  - Best-guess recommendations with knowledge gap analysis
  - Complete YAML configuration generation

### Added - Workflows

- **Code Review Workflow** - LangGraph-based workflow for systematic code review with configurable rubrics
- **Base Workflow Service** - Abstract class for creating custom workflows with type-safe generics
- **Generation Strategies** - Pluggable prompting strategies (standard, chain-of-thought, few-shot, verbalized-sampling)

### Fixed

- **BUG-001**: Pareto analysis accepted only exactly 2 axes (now defaults to quality-cost)
- **BUG-002**: Partial experiment JSON results were invalid (now writes valid arrays incrementally)
- **BUG-003**: Error messages missing helpful context (now includes test number and available options)
- **BUG-004**: Optimal config export crashed with special characters (now uses safe YAML serialization)
- **BUG-005**: Resume flag ignored already-completed tests (now properly skips completed tests)
- **BUG-006**: Dry-run mode still initialized workflow services (now skips initialization entirely)

### Technical Details

- **Python 3.11+** required
- **Test Coverage**: 80% for core algorithms (Taguchi, Pareto, main effects)
- **Dependencies**: Typer, Rich, LiteLLM, LangGraph, Matplotlib, NumPy, SciPy, PyYAML, Pydantic 2.0
- **Architecture**: Clean separation of concerns (core, experiments, evaluation, optimization, workflows, cli)
- **Type Safety**: Pydantic validation for all configs and data models
- **Async-First**: Async/await patterns for LLM calls

### Validated

- **Real-World Testing** - Rubric.py code review experiment:
  - 8/8 tests completed successfully
  - Cost: $0.40 for complete L8 experiment
  - Discoveries:
    - Context size: 48.2% contribution to quality
    - Model choice: 38.5% contribution (Sonnet 4.5 +6.5% over Haiku)
    - Chain-of-thought: -1.9% quality impact (counterintuitive finding!)
    - Temperature: 3.5% contribution (minimal impact)
  - Quality improvement: +16.9% from baseline
  - 5+ real issues identified in production code

### Performance

- L8 experiment (8 tests) completes in 5-10 minutes (depending on model)
- Main effects analysis: <5 seconds
- Pareto visualization: <2 seconds
- Evaluation caching reduces repeat costs by 90%+

### Known Limitations (MVP)

- CLI-only (no web UI)
- Sequential execution (no parallelization)
- JSON storage (no database)
- L8 array only (L16/L18 deferred to v0.2)
- Rubric evaluator only (pairwise A/B deferred to v0.2)

## [Unreleased]

### v0.2.0 - Web UI + API (Target: December 2025)

**Status:** Planning complete, implementation starting

#### Planned - Web UI (Streamlit)
- Experiment configuration UI (visual builder + YAML editor)
- Real-time experiment progress (WebSocket updates)
- Interactive results dashboard (main effects + Pareto charts)
- Knowledge base explorer (browse, search, vote on insights)
- Experiment history and comparison
- User profile and settings

#### Planned - REST API (FastAPI)
- `POST /api/experiments` - Create and run experiments
- `GET /api/experiments` - List all experiments
- `GET /api/experiments/:id` - Get experiment details/status
- `POST /api/analyze/*` - Run analysis (main effects, Pareto)
- `GET /api/knowledge/*` - Browse knowledge base
- `WS /ws/experiments/:id` - Real-time updates
- OpenAPI/Swagger documentation at `/docs`

#### Planned - Authentication
- User signup/login with JWT tokens
- Encrypted API key storage (BYO LLM API keys)
- Session management
- User profile management

#### Planned - Database
- SQLite for local development
- SQLAlchemy ORM with Alembic migrations
- Persistent experiment history
- Knowledge base storage with voting

#### Technical Details
- **Duration:** 6 weeks (120-150 hours)
- **Stack:** FastAPI + Uvicorn + Streamlit + SQLAlchemy
- **Release Plan:**
  - v0.2.0-alpha (Week 4) - Internal testing
  - v0.2.0-beta (Week 5) - External beta testers
  - v0.2.0 (Week 6) - Public release

**Reference:** `specs/002-web-ui-api/`

---

### v0.3.0 - Scale & Collaboration (Future)

- Team workspaces and shared knowledge bases
- PostgreSQL migration for hosted SaaS
- Parallel experiment execution (8x speedup)
- L16/L18 orthogonal arrays (6-8 variables)
- Experiment comparison tools
- React migration (if Streamlit proves limiting)

### v1.0.0 - SaaS & Enterprise (Future)

- Hosted SaaS platform with managed infrastructure
- Enterprise features (SSO, audit logs, SLA)
- CI/CD integrations (GitHub Actions, GitLab CI)
- Workflow marketplace for sharing configurations
- Advanced evaluators (pairwise A/B, ensemble judging)

---

## Version History

- **0.1.0** (2025-10-26) - Initial release with MVP feature set

---

**Note**: This is the first public release of TesseractFlow. While tested in production scenarios, please report any issues on [GitHub Issues](https://github.com/markramm/TesseractFlow/issues).
