# Core Module Reference

This document summarizes the primary public classes and functions exposed by TesseractFlow. Import paths are relative to the `tesseract_flow` package.

---

## `tesseract_flow.core`

### `BaseWorkflowService`
- Generic base class for LangGraph-powered workflows.
- Subclass and implement `_build_workflow()` to return a compiled `StateGraph`.
- Provides `run(input_model)` which measures runtime, collects metadata, and converts LangGraph output into the declared `OutputModel`.

### Configuration Models (`core.config`)
- `ExperimentConfig` – Validates YAML experiments, enforces variable/weight rules, computes hashes, and derives metadata.
- `TestConfiguration` – Represents a single Taguchi trial with normalized identifiers.
- `ExperimentRun` – Tracks execution status, normalization statistics, baseline metadata, and aggregated analysis.
- `WorkflowConfig` – Base class for workflow-specific settings (extended by code review workflow).
- `ExperimentMetadata` – Captures version info, dependency hashes, and reproducibility data.
- `TestResult` – Stores raw evaluator payloads, normalized metrics, and derived utility scores.

### Strategies (`core.strategies`)
- `GenerationStrategy` – Protocol defining how workflows interact with language models.
- `StandardStrategy` – Default implementation using LiteLLM chat completion calls.
- `GENERATION_STRATEGIES` – Registry mapping strategy names to callables.
- `register_strategy(name, factory)` / `get_strategy(name)` – Runtime extension hooks for custom strategies.

### Exceptions (`core.exceptions`)
- `ConfigurationError`, `ExperimentError`, `EvaluationError`, `CacheError`, etc. – Domain-specific error types surfaced throughout the CLI.

---

## `tesseract_flow.experiments`

### Taguchi utilities (`experiments.taguchi`)
- `L8_ARRAY` and `generate_test_configs()` – Produce orthogonal test plans for 4–7 variables.

### Experiment execution (`experiments.executor`)
- `ExperimentExecutor` – Orchestrates workflow execution, evaluator calls, persistence, and resume logic.
- `run_single_test()` – Executes a single configuration and records metrics.
- `run()` – Executes an entire Taguchi run with optional progress callbacks.
- `load_run(path)` / `save_run(path, run)` – JSON serialization helpers used by the CLI.

### Analysis (`experiments.analysis`)
- `MainEffectsAnalyzer` – Computes main effects, sum-of-squares, and contribution percentages.
- `identify_optimal_config()` – Returns the best configuration and associated statistics.
- `calculate_quality_improvement()` – Computes baseline vs optimal uplift.
- `compare_configurations()` – Generates baseline/optimal comparison metadata.
- `export_optimal_config(path, configuration)` – Writes YAML for downstream automation.

---

## `tesseract_flow.evaluation`

### Metrics (`evaluation.metrics`)
- `DimensionScore` – Normalized rubric dimension with optional weight.
- `QualityScore` – Aggregates dimension scores into a single overall metric.

### Rubric evaluator (`evaluation.rubric`)
- `RubricEvaluator` – LiteLLM-backed evaluator with retry logic, caching hooks, and structured parsing.
- `build_prompt()` – Generates the system/user prompts containing rubric instructions.
- `parse_response()` – Validates model output and converts it into `QualityScore` objects.

### Cache (`evaluation.cache`)
- `CacheBackend` – Protocol for cache implementations.
- `FileCacheBackend` – Default implementation storing JSON responses on disk with hashing.

---

## `tesseract_flow.optimization`

### Utility (`optimization.utility`)
- `UtilityFunction` – Applies min-max normalization to cost/latency and computes weighted utilities.

### Pareto (`optimization.pareto`)
- `ParetoPoint` / `ParetoFrontier` – Identify non-dominated points, filter by budget, and render matplotlib charts.

---

## `tesseract_flow.workflows`

### Code Review Workflow (`workflows.code_review`)
- `CodeReviewWorkflow` – LangGraph workflow orchestrating analysis and suggestion generation via registered strategies.
- `CodeReviewInput` / `CodeReviewOutput` / `CodeIssue` – Pydantic models describing workflow inputs and structured outputs.
- Helper functions for prompt rendering, metadata capture, and strategy instantiation.

---

## CLI Packages (`tesseract_flow.cli`)

- `main.app` – Root Typer application with global `--log-level` and `--version` options.
- `experiment.run` – Execute Taguchi experiments with dry run, resume, cache, and instruction flags.
- `experiment.analyze` – Main effects reporting and optimal configuration export.
- `experiment.status` – Inspect saved runs and highlight incomplete tests.
- `experiment.validate` – Perform configuration linting without execution.
- `visualize.pareto` – Render Pareto frontiers with customizable axes and budget filters.

Use `python -m tesseract_flow.cli.main --help` or `tesseract --help` after installation to browse full option lists.
