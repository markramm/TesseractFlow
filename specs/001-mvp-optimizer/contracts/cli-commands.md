# CLI Command Contracts

**Feature**: 001-mvp-optimizer | **Date**: 2025-10-25

This document specifies the command-line interface for TesseractFlow MVP.

---

## Command Structure

```bash
tesseract <command> [subcommand] [arguments] [options]
```

**Commands:**
- `experiment` - Run and manage experiments
- `analyze` - Analyze experiment results
- `visualize` - Generate visualizations

---

## `tesseract experiment run`

Run a Taguchi L8 experiment.

### Synopsis

```bash
tesseract experiment run <config-file> [options]
```

### Arguments

- `config-file` (required) - Path to experiment configuration YAML

### Options

- `--output, -o` - Output JSON file path (default: `results_{timestamp}.json`)
- `--verbose, -v` - Enable verbose logging
- `--dry-run` - Validate config and show test configurations without running
- `--resume` - Resume failed experiment from last completed test

### Examples

```bash
# Run experiment with default output
tesseract experiment run experiments/code_review.yaml

# Specify output file
tesseract experiment run experiments/code_review.yaml -o results.json

# Dry run to validate config
tesseract experiment run experiments/code_review.yaml --dry-run

# Resume failed experiment
tesseract experiment run experiments/code_review.yaml --resume
```

### Output

**Success:**
```
✓ Loaded experiment config: code_review_optimization
✓ Generated 8 test configurations from L8 array
✓ Running test 1/8... [████████░░] 2.3s
✓ Running test 2/8... [████████░░] 2.1s
...
✓ All tests completed in 18.7s
✓ Results saved to: results_20251025_143022.json

Summary:
  Tests: 8/8 completed
  Quality range: 0.65 - 0.92
  Cost range: $0.002 - $0.015
  Best utility: Test #7 (0.89)

Next steps:
  tesseract analyze results_20251025_143022.json
```

**Error (invalid config):**
```
✗ Error: Invalid experiment configuration
  - Variable count must be 4-7 (found: 3)
  - Variable 'temperature' level_1 and level_2 are identical

Fix these issues and try again.
```

### Exit Codes

- `0` - Success
- `1` - Invalid configuration
- `2` - Experiment execution failed
- `3` - File I/O error

---

## `tesseract analyze`

Analyze experiment results and show main effects.

### Synopsis

```bash
tesseract analyze <results-file> [options]
```

### Arguments

- `results-file` (required) - Path to experiment results JSON

### Options

- `--format, -f` - Output format: `table` (default), `json`, `markdown`
- `--export` - Export optimal config to YAML file
- `--show-chart` - Display main effects bar chart (requires matplotlib)

### Examples

```bash
# Analyze with table output
tesseract analyze results.json

# Export analysis to JSON
tesseract analyze results.json -f json > analysis.json

# Export optimal config
tesseract analyze results.json --export optimal_config.yaml

# Show interactive chart
tesseract analyze results.json --show-chart
```

### Output

**Table format (default):**
```
Main Effects Analysis
═══════════════════════════════════════════════════════

Variable            Effect    Level 1   Level 2   Contribution
──────────────────────────────────────────────────────────────
temperature         +0.120    0.680     0.800     35.2%
context_size        +0.100    0.730     0.830     28.5%
model               +0.080    0.740     0.820     23.1%
generation_strategy +0.050    0.770     0.820     13.2%
──────────────────────────────────────────────────────────────
Total                                              100.0%

Optimal Configuration:
  temperature: 0.7 (level 2)
  context_size: full_module (level 2)
  model: anthropic/claude-3.5-sonnet (level 2)
  generation_strategy: chain_of_thought (level 2)

  Expected utility: 0.89
  Expected quality: 0.92
  Expected cost: $0.012
  Expected latency: 3.2s
```

**JSON format:**
```json
{
  "main_effects": {
    "temperature": {
      "effect_size": 0.120,
      "avg_level_1": 0.680,
      "avg_level_2": 0.800,
      "contribution_pct": 35.2
    },
    ...
  },
  "optimal_config": {
    "config_values": {
      "temperature": 0.7,
      "model": "anthropic/claude-3.5-sonnet",
      "context_size": "full_module",
      "generation_strategy": "chain_of_thought"
    },
    "expected_metrics": {
      "utility": 0.89,
      "quality": 0.92,
      "cost": 0.012,
      "latency": 3200
    }
  }
}
```

### Exit Codes

- `0` - Success
- `1` - Results file not found or invalid
- `2` - Analysis computation failed

---

## `tesseract visualize pareto`

Generate Pareto frontier visualization.

### Synopsis

```bash
tesseract visualize pareto <results-file> [options]
```

### Arguments

- `results-file` (required) - Path to experiment results JSON

### Options

- `--x-axis` - Metric for X-axis: `cost` (default), `latency`
- `--y-axis` - Metric for Y-axis: `quality` (default)
- `--output, -o` - Output image file (PNG, SVG, or PDF)
- `--interactive` - Show interactive plot window
- `--budget` - Highlight configurations within cost budget

### Examples

```bash
# Generate PNG with default axes
tesseract visualize pareto results.json -o pareto.png

# Interactive plot
tesseract visualize pareto results.json --interactive

# Quality vs latency
tesseract visualize pareto results.json --x-axis latency -o quality_latency.svg

# Highlight budget-constrained options
tesseract visualize pareto results.json --budget 0.01 -o pareto_budget.png
```

### Output

**Generated visualization:**
- Scatter plot with cost on X-axis, quality on Y-axis
- Bubble size represents latency
- Pareto-optimal points highlighted in color
- Dominated points shown in gray
- Budget threshold line (if --budget specified)
- Annotations with test numbers

**Console output:**
```
✓ Loaded 8 test results
✓ Computed Pareto frontier: 3 optimal points
✓ Generated visualization: pareto.png

Pareto-optimal configurations:
  Test #3: quality=0.75, cost=$0.002, latency=1.8s (best cost)
  Test #7: quality=0.85, cost=$0.005, latency=2.3s (balanced)
  Test #1: quality=0.92, cost=$0.012, latency=3.1s (best quality)

Recommendation:
  For budget ≤ $0.01: Choose Test #7 (quality=0.85, cost=$0.005)
```

### Exit Codes

- `0` - Success
- `1` - Results file not found or invalid
- `2` - Visualization generation failed

---

## `tesseract experiment status`

Check status of running or completed experiments.

### Synopsis

```bash
tesseract experiment status [experiment-id]
```

### Arguments

- `experiment-id` (optional) - Specific experiment ID (default: latest)

### Examples

```bash
# Check latest experiment
tesseract experiment status

# Check specific experiment
tesseract experiment status exp_20251025_001
```

### Output

```
Experiment: exp_20251025_001
Status: RUNNING
Progress: 5/8 tests completed (62%)
Elapsed: 12.3s
Estimated remaining: 6.1s

Completed tests:
  Test 1: quality=0.85, cost=$0.004, latency=2.1s ✓
  Test 2: quality=0.78, cost=$0.003, latency=1.9s ✓
  Test 3: quality=0.92, cost=$0.012, latency=3.4s ✓
  Test 4: quality=0.71, cost=$0.002, latency=1.7s ✓
  Test 5: quality=0.88, cost=$0.006, latency=2.5s ✓

Running:
  Test 6: In progress... (1.2s elapsed)
```

---

## Global Options

Available for all commands:

- `--help, -h` - Show help message
- `--version` - Show version information
- `--config` - Path to global config file (default: `~/.tesseract/config.yaml`)
- `--log-level` - Logging level: `DEBUG`, `INFO` (default), `WARNING`, `ERROR`

### Examples

```bash
# Show help for specific command
tesseract experiment run --help

# Set log level
tesseract experiment run config.yaml --log-level DEBUG

# Show version
tesseract --version
# Output: TesseractFlow 0.1.0
```

---

## Configuration File Format

### Experiment Config (YAML)

```yaml
# experiments/code_review.yaml

name: "code_review_optimization"
workflow: "code_review"

variables:
  temperature:
    level_1: 0.3
    level_2: 0.7

  model:
    level_1: "openai/gpt-4"
    level_2: "anthropic/claude-3.5-sonnet"

  context_size:
    level_1: "file_only"
    level_2: "full_module"

  generation_strategy:
    level_1: "standard"
    level_2: "chain_of_thought"

utility_weights:
  quality: 1.0
  cost: 0.1
  time: 0.05

workflow_config:
  rubric:
    clarity:
      description: "Is the code review clear and actionable?"
      scale: "1-10"
    accuracy:
      description: "Are identified issues accurate?"
      scale: "1-10"
    completeness:
      description: "Does review cover all important aspects?"
      scale: "1-10"

seed: 42
```

---

## Error Handling

All commands provide clear error messages and recovery suggestions:

**Example (missing file):**
```bash
$ tesseract analyze missing.json

✗ Error: Results file not found
  File: missing.json

  Did you mean one of these?
    - results_20251025_143022.json
    - results_20251025_140512.json

  Or run a new experiment:
    tesseract experiment run experiments/code_review.yaml
```

**Example (invalid format):**
```bash
$ tesseract analyze corrupted.json

✗ Error: Invalid results file format
  File: corrupted.json
  Issue: Missing required field 'test_configurations'

  This file may be from an older version of TesseractFlow
  or may be corrupted. Try running the experiment again.
```

---

## Future Commands (Post-MVP)

Not in MVP scope but planned:

- `tesseract experiment compare <results1> <results2>` - Compare two experiments
- `tesseract experiment history` - List all past experiments
- `tesseract config validate <config-file>` - Validate config without running
- `tesseract export report <results-file>` - Generate PDF report

---

## Implementation Notes

**CLI Framework:** Typer (type-safe, modern Python CLI)

**Progress Display:** Rich library for progress bars, tables, syntax highlighting

**File Operations:** Pathlib for cross-platform path handling

**Error Messages:** Structured with emojis (✓ ✗), colors, actionable suggestions

**Exit Codes:** Standard Unix convention (0=success, non-zero=error)
