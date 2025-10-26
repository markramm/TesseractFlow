# Changelog

All notable changes to TesseractFlow will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

### Planned for v0.2

- Web dashboard for experiment visualization (Streamlit/Gradio)
- Parallel execution for 8x speedup
- Additional workflow examples (summarization, data extraction)
- L16/L18 orthogonal arrays for 6-8 variables
- Experiment comparison tools

### Planned for v0.3

- Human-in-the-loop (HITL) approval queue integration
- PostgreSQL backend for experiment history
- Advanced evaluators (pairwise comparisons, ensemble judging)
- Multi-experiment analysis and meta-learning

### Planned for v1.0

- Hosted SaaS version with managed infrastructure
- Team collaboration features
- CI/CD integrations (GitHub Actions, GitLab CI)
- Workflow marketplace for sharing configurations
- Enterprise support offering

---

## Version History

- **0.1.0** (2025-10-26) - Initial release with MVP feature set

---

**Note**: This is the first public release of TesseractFlow. While tested in production scenarios, please report any issues on [GitHub Issues](https://github.com/markramm/TesseractFlow/issues).
