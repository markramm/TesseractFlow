# Quickstart

This quickstart walks through running the built-in code review optimization experiment end-to-end. By the end you will have:

1. Loaded the sample Taguchi L8 experiment configuration.
2. Executed all eight trials with cached rubric evaluation responses.
3. Analyzed the resulting quality, cost, and latency trade-offs.
4. Visualized the Pareto frontier and exported the recommended configuration.

---

## Prerequisites

- Python 3.11 or newer.
- An API key for at least one LiteLLM-supported provider (OpenRouter, Anthropic, OpenAI, etc.).
- Git (for cloning this repository) and virtualenv tooling such as `uv`, `pipenv`, or `python -m venv`.

> The CLI supports offline execution using the bundled cache. Real LLM access is required to record fresh evaluations.

---

## 1. Install TesseractFlow from source

```bash
# Clone the repository
$ git clone https://github.com/markramm/TesseractFlow.git
$ cd TesseractFlow

# Create and activate a virtual environment (example using venv)
$ python -m venv .venv
$ source .venv/bin/activate

# Install the package and CLI
(.venv) $ pip install -e .
```

The editable install exposes the `tesseract` CLI entrypoint and brings in required dependencies such as Typer, Rich, LiteLLM, and matplotlib.

---

## 2. Configure environment variables

Export any provider credentials required by LiteLLM. The examples below use OpenRouter:

```bash
(.venv) $ export OPENROUTER_API_KEY="sk-your-key"
```

You can also store the key inside a `.env` file that your shell or process manager loads before running experiments.

---

## 3. Inspect the sample experiment

The repository ships with a ready-to-run configuration:

```bash
(.venv) $ cat examples/code_review/experiment_config.yaml
```

This file defines four binary variables (temperature, model, context window, and generation strategy), utility weights, and the rubric used to grade each review.

---

## 4. Perform a dry run

Validate the configuration and preview the Taguchi test matrix without executing any LLM calls:

```bash
(.venv) $ tesseract experiment run examples/code_review/experiment_config.yaml --dry-run
```

You should see the inferred eight test configurations along with summary statistics and resume hints.

---

## 5. Execute the experiment

Run all eight tests, resuming from previous partial results if necessary:

```bash
(.venv) $ tesseract experiment run \
    examples/code_review/experiment_config.yaml \
    --output results.json \
    --record-cache \
    --verbose
```

Key behaviours during execution:

- Progress is displayed with Rich spinners and bars.
- Partial results are written to `results.json` after each trial.
- Evaluation responses are cached under `~/.cache/tesseract_flow/evaluations/` when `--record-cache` is supplied.
- Use `--use-cache` to replay cached responses without performing new API calls.

If the command exits early, re-run it with `--resume --output results.json` to continue from the saved state.

---

## 6. Analyze results

Generate main effects, compare baseline versus optimal configurations, and optionally export the recommended YAML:

```bash
(.venv) $ tesseract experiment analyze results.json --format table --export optimal.yaml
```

Useful variations:

- `--format json` or `--format markdown` for automated pipelines.
- Omit `--export` to skip writing the optimal configuration file.

The analysis output highlights each variable's contribution, shows the baseline quality, and reports the quality improvement percentage.

---

## 7. Visualize the Pareto frontier

Render a PNG chart that illustrates quality/cost trade-offs across all trials:

```bash
(.venv) $ tesseract visualize pareto results.json --output pareto.png --budget 0.010
```

This produces both a console summary of Pareto-optimal configurations and a saved image containing labelled points, latency-driven bubble sizes, and an optional budget threshold.

Use `--y-axis utility` or `--x-axis latency` to explore alternative views, and omit `--output` to display the chart interactively (if a display server is available).

---

## 8. Next steps

- Edit `examples/code_review/experiment_config.yaml` to add additional variables or adjust utility weights.
- Point the workflow at your own repository by updating `workflow_config.sample_code_path`.
- Integrate the underlying `ExperimentExecutor` or `RubricEvaluator` classes into custom automation by importing them from `tesseract_flow.experiments` and `tesseract_flow.evaluation`.

Happy optimizing!
