# Interpreting Results

After running an experiment you receive a JSON file (default `results.json`) plus optional CLI summaries. This guide explains how to interpret those outputs and translate them into workflow improvements.

---

## 1. Inspect the run summary

Every run stores metadata alongside results:

- **`experiment_id`** – Deterministic UUID derived from the configuration hash.
- **`started_at` / `completed_at`** – ISO 8601 timestamps that let you measure total runtime.
- **`baseline`** – Captures the initial configuration (Taguchi row 1) and its quality score for comparison.
- **`normalization`** – Min/max values for cost and latency used in the utility function.

Use the CLI to display the latest run at any time:

```bash
$ tesseract experiment status results.json
```

This command highlights unfinished tests, shows resume hints, and summarizes the best configuration discovered so far.

---

## 2. Evaluate quality metrics

The evaluator returns structured quality data per trial:

- `score.overall` – Weighted aggregate between 0 and 1.
- `score.dimensions` – Individual rubric dimensions, each normalized between 0 and 1.
- `raw_response` – Unmodified JSON returned by the LLM before normalization.

### Troubleshooting evaluator output

- **Low variance** – If every trial produces nearly identical scores, revisit rubric wording or enable `--instructions` to provide more context.
- **Parsing failures** – Inspect the raw response to confirm the model followed the schema. Consider switching providers or temperature levels.
- **Baseline worse than optimal** – Expected! Use the improvement percentage to quantify gains relative to the starting point.

---

## 3. Understand main effects

Run the analysis command to compute variable contributions:

```bash
$ tesseract experiment analyze results.json --format table
```

The Rich table lists each variable, its effect size, average utility per level, and contribution percentage. Focus your iteration on variables with the largest contributions.

- **High contribution (>30%)** – Strong leverage. Standardize on the better-performing level and explore additional variants.
- **Medium contribution (10–30%)** – Influential but secondary. Tune alongside high-impact variables.
- **Low contribution (<10%)** – Minimal effect. Consider removing to reduce experiment complexity.

The command also reports the quality improvement percentage compared to the baseline and exports the recommended configuration when `--export` is supplied.

---

## 4. Compare configurations

Inside the JSON results the `analysis` block includes:

- `optimal_configuration` – Full variable assignment for the best-scoring trial.
- `baseline_configuration` – Original Taguchi row for reference.
- `quality_improvement_pct` – Percent uplift relative to the baseline score.
- `top_tests` – Utility-sorted leaderboard to help you inspect near-optimal alternatives.

Use these data to brief stakeholders or update CI/CD pipelines with concrete configuration changes.

---

## 5. Visualize trade-offs

The Pareto frontier reveals how quality trades off against cost and latency:

```bash
$ tesseract visualize pareto results.json --output pareto.png --budget 0.012
```

Interpretation tips:

- Points on the frontier are non-dominated (no other trial is better on both axes).
- Bubble size encodes latency – smaller bubbles indicate faster responses.
- The optional budget line highlights tests that meet cost constraints.

Check the console output for a textual summary of Pareto-optimal configurations sorted by quality, along with budget-aware recommendations.

---

## 6. Decide next actions

1. **Adopt the recommended configuration** – Apply the optimal levels to your production workflow.
2. **Rerun with refined variables** – Swap out low-contribution variables for new hypotheses.
3. **Adjust utility weights** – Rebalance priorities if cost or latency constraints change.
4. **Record evaluator cache** – Keep `--record-cache` enabled to compare historical runs consistently.

By iterating on these steps you can continuously improve LLM workflows without retraining models.
