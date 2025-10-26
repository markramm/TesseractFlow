# Configuration Reference

TesseractFlow experiments are described with YAML files that map directly to the `ExperimentConfig` Pydantic model. This guide explains every supported section and provides tips for creating valid configurations that work with the Taguchi L8 design.

> Use `tesseract experiment validate <config.yaml>` to lint a configuration and preview inferred metadata before running a full experiment.

---

## Top-level fields

| Field | Required | Description |
| ----- | -------- | ----------- |
| `name` | ✅ | Unique experiment identifier. Used for output file naming and run metadata. |
| `workflow` | ✅ | Name of the workflow to execute. The distribution ships with the `code_review` workflow. |
| `variables` | ✅ | Mapping of experimental variables to two discrete levels. Each value may be any JSON-serializable type. |
| `utility_weights` | ✅ | Weights used to balance quality, cost, and latency inside the utility function. |
| `workflow_config` | ✅ | Workflow-specific configuration passed to the workflow service. Structure depends on the workflow. |
| `seed` | Optional | Integer used to seed deterministic operations (sampling, evaluator shuffling). |
| `metadata` | Optional | Arbitrary key/value metadata stored alongside experiment results. |

All other keys are validated and preserved by the underlying model; unexpected sections raise a `ConfigurationError`.

---

## Variables block

Each variable must specify exactly **two levels** to align with the Taguchi L8 design. Levels can be numbers, strings, or structured objects. Example:

```yaml
variables:
  temperature:
    level_1: 0.3
    level_2: 0.7
  model:
    level_1: "openrouter/anthropic/claude-3.5-sonnet"
    level_2: "openrouter/openai/gpt-4.1-mini"
  context_size:
    level_1: "file_only"
    level_2: "full_module"
  generation_strategy:
    level_1:
      name: standard
    level_2:
      name: chain_of_thought
      max_steps: 3
```

### Validation rules

- A minimum of 4 and a maximum of 7 variables are supported.
- Variable identifiers must be snake_case and begin with a letter.
- Each `level_1`/`level_2` entry is required. Additional keys trigger validation errors.
- Structured levels are preserved as dictionaries inside `TestConfiguration` instances and emitted in result files.

---

## Utility weights

Utility scores are computed per test using the normalized metrics and the provided weights:

```text
utility = (quality_weight × quality)
          - (cost_weight × normalized_cost)
          - (time_weight × normalized_latency)
```

Guidance:

- All weights must be non-negative numbers.
- At least one weight must be non-zero.
- Increase `cost` or `time` weights to penalize expensive or slow configurations.

---

## Workflow configuration

The `workflow_config` block is passed straight into the workflow service. For the built-in `code_review` workflow the following keys are recognized:

| Key | Description |
| --- | ----------- |
| `rubric` | Mapping of rubric dimension identifiers to metadata (`description`, `scale`, optional `weight`). |
| `sample_code_path` | Path to the source file evaluated during dry runs and tests. |
| `language` | Optional override for language detection (defaults to auto-detected via file suffix). |
| `prompt_overrides` | Optional overrides for the default system/user prompts. |

Rubric definitions must include at least one dimension. Each dimension becomes a `DimensionScore` in the evaluator output and contributes to the aggregate quality score.

---

## Advanced options

### Cache controls

Experiment runs can reuse evaluator outputs via the FileCache backend. Supply cache flags on the CLI:

- `--use-cache` – Replay cached responses if present.
- `--record-cache` – Persist all responses using hashes derived from prompt, model, and temperature.
- `--cache-dir` – Override the default cache location.

### Resume support

Specify `--resume --output <results.json>` when re-running a command to resume from partial results. The executor ensures previously completed trials are skipped and maintains consistent normalization metadata.

### Extra evaluator instructions

Use `--instructions "text"` to append additional rubric context when invoking `experiment run`. This is particularly helpful when adapting the code review workflow to other languages or repositories.

---

## Result files

Experiments produce JSON documents adhering to the `ExperimentRun` model. Key sections include:

- `experiment_id`, `name`, and `workflow`
- `test_configurations` – ordered list describing each Taguchi trial
- `results` – per-test quality metrics, raw evaluator responses, and cost/time measurements
- `normalization` – min/max statistics used for utility calculations
- `analysis` – baseline metadata, optimal configuration summary, and quality improvement percentages

These files feed directly into `tesseract experiment analyze` and `tesseract visualize pareto`.
