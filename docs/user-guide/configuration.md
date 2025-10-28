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

### Built-in Variables for Reasoning and Verbalized Sampling

TesseractFlow provides mixins that add reasoning and verbalized sampling capabilities to workflows. These variables can be included in any experiment configuration:

#### Reasoning Parameters

```yaml
variables:
  reasoning_enabled:
    level_1: 'false'    # Standard generation (no reasoning traces)
    level_2: 'true'     # Enable extended reasoning before output

  reasoning_visibility:
    level_1: visible    # Include reasoning in output
    level_2: hidden     # Generate reasoning but exclude from output

  max_reasoning_tokens:
    level_1: standard   # Default token budget for reasoning
    level_2: extended   # Increased token budget for complex reasoning
```

**When to use reasoning parameters**:
- **Fiction/Creative Writing**: Enable reasoning for complex scenes, character development, or discovery workflows
- **Code Review**: Enable reasoning for architectural analysis or complex refactoring suggestions
- **Analytical Tasks**: Enable reasoning when tasks require multi-step inference or trade-off evaluation

**Key findings from experiments** (docs/evaluator_comparison_gpt5mini.md:161):
- Fiction scenes benefit from `reasoning_enabled=true` but `max_reasoning_tokens=standard` (31% contribution)
- Progressive discovery benefits from `reasoning_enabled=true` with `max_reasoning_tokens=extended` (8.3% contribution)
- Dialogue enhancement shows minimal benefit from reasoning (<5% contribution)

#### Verbalized Sampling Parameters

```yaml
variables:
  verbalized_sampling:
    level_1: none                 # Single generation (no sampling)
    level_2: self_consistency     # Generate multiple samples, select best

  n_samples:
    level_1: '3'    # Generate 3 samples (lower cost, faster)
    level_2: '5'    # Generate 5 samples (higher quality, slower)
```

**When to use verbalized sampling**:
- **Character Development**: Use `n_samples=5` for exploring character motivations and arcs
- **Discovery Workflows**: Use `n_samples=3` to explore multiple narrative directions
- **High-Stakes Outputs**: Use when output quality is more important than cost/latency

**Key findings from experiments** (docs/evaluator_comparison_gpt5mini.md:158):
- `verbalized_sampling=none` recommended for most workflows (strong negative effect in Fiction -36.6%, Character -36.8%)
- Character development benefits from `n_samples=5` when not using verbalized sampling (33.5% contribution)
- Progressive discovery optimal at `n_samples=3` (30.7% contribution)

#### Example: Fiction Scene with Reasoning

```yaml
name: fiction_scene_reasoning_test
workflow: fiction_scene
variables:
  temperature:
    level_1: 0.5
    level_2: 0.9
  context_depth:
    level_1: minimal
    level_2: full
  reasoning_enabled:
    level_1: 'false'
    level_2: 'true'
  verbalized_sampling:
    level_1: none
    level_2: self_consistency
  n_samples:
    level_1: '3'
    level_2: '5'
  reasoning_visibility:
    level_1: visible
    level_2: hidden
  max_reasoning_tokens:
    level_1: standard
    level_2: extended

utility_weights:
  quality: 0.8
  cost: 0.15
  time: 0.05
```

See `experiments/wave4_fiction_reasoning_vs_gpt5mini.yaml` for complete working example.

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
