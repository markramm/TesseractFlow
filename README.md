# TesseractFlow

**Multi-dimensional LLM workflow optimization powered by Taguchi Design of Experiments**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Status: Alpha](https://img.shields.io/badge/status-alpha-orange.svg)]()

---

## Overview

TesseractFlow helps teams systematically improve LLM workflows without resorting to expensive model fine-tuning. By combining Taguchi orthogonal arrays, rubric-based evaluation, and multi-objective optimization, you can iterate on prompts, context windows, models, and strategies in hours instead of weeks.

### Key capabilities

- **Efficient experimentation** – Generate eight Taguchi L8 trials that cover four to seven variables.
- **Quality evaluation** – Score results using rubric-driven LiteLLM calls with caching and retries.
- **Utility optimization** – Balance quality, cost, and latency using configurable weights.
- **Analysis & reporting** – Compute main effects, compare configurations, and export YAML recommendations.
- **Visualization** – Render Pareto frontiers highlighting non-dominated trade-offs.
- **Rich CLI** – Run, resume, validate, analyze, and visualize experiments from the terminal.

---

## Installation

The project targets Python 3.11+. Until published on PyPI, install from source:

```bash
$ git clone https://github.com/markramm/TesseractFlow.git
$ cd TesseractFlow
$ python -m venv .venv
$ source .venv/bin/activate
(.venv) $ pip install -e .
```

This installs the `tesseract` CLI along with required dependencies (Typer, Rich, LiteLLM, LangGraph, matplotlib, NumPy, PyYAML, etc.).

Set the appropriate provider API keys before running experiments, e.g. `export OPENROUTER_API_KEY=...`.

---

## Quick start

1. **Preview the configuration**
   ```bash
   tesseract experiment run examples/code_review/experiment_config.yaml --dry-run
   ```
2. **Execute the Taguchi experiment**
   ```bash
   tesseract experiment run examples/code_review/experiment_config.yaml \
     --output results.json --record-cache --verbose
   ```
3. **Analyze main effects and export recommendations**
   ```bash
   tesseract experiment analyze results.json --format table --export optimal.yaml
   ```
4. **Visualize the Pareto frontier**
   ```bash
   tesseract visualize pareto results.json --output pareto.png --budget 0.010
   ```

Refer to [docs/user-guide/quickstart.md](docs/user-guide/quickstart.md) for a detailed walkthrough.

---

## Documentation

- [Quickstart](docs/user-guide/quickstart.md)
- [Configuration Reference](docs/user-guide/configuration.md)
- [Interpreting Results](docs/user-guide/interpreting-results.md)
- [API Overview](docs/api/core-modules.md)
- [Development Setup](docs/development/setup.md)
- [PR Troubleshooting](docs/development/git_pr_troubleshooting.md)

---

## CLI commands

```text
$ tesseract --help
Usage: tesseract [OPTIONS] COMMAND [ARGS]...

Options:
  -l, --log-level LEVEL  Set global log level (critical, error, warning, info, debug).
  --version              Show the TesseractFlow version and exit.
  --help                 Show this message and exit.
```

Available subcommands:

- `tesseract experiment run` – Execute experiments with dry-run, resume, cache, and extra instruction options.
- `tesseract experiment analyze` – Main effects, baseline comparison, and YAML export.
- `tesseract experiment status` – Inspect partial runs and resume hints.
- `tesseract experiment validate` – Lint configuration files without running tests.
- `tesseract visualize pareto` – Plot quality vs cost (or any supported axes) with optional budget filtering.

---

## Project structure

```
tesseract_flow/
├── core/          # Base workflow service, configuration models, strategies, exceptions
├── evaluation/    # Rubric evaluator, metrics, caching
├── experiments/   # Taguchi utilities, executor, analysis helpers
├── optimization/  # Utility function and Pareto frontier implementation
├── workflows/     # LangGraph workflows (code_review example)
└── cli/           # Typer-powered CLI entry points
```

Unit tests live under `tests/` with integration coverage for CLI flows, evaluation, and visualization.

---

## Contributing

Contributions and feedback are welcome! Please open an issue to discuss major features or bug reports. When submitting patches:

- Run `pytest` (with coverage enabled) to ensure tests pass.
- Include documentation updates for new features or CLI options.
- Follow the coding patterns established in `tesseract_flow/core` and `tesseract_flow/cli`.

---

## License

TesseractFlow is released under the [MIT License](LICENSE).
