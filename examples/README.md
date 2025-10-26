# Examples

The `code_review` example demonstrates how to optimize an LLM code review workflow with the Taguchi L8 design.

## Directory structure

```
examples/
└── code_review/
    ├── experiment_config.yaml   # Ready-to-run Taguchi configuration
    └── sample_code/
        ├── example1.py          # Baseline snippet used during runs
        └── example2.py          # Additional file for experimentation
```

## Running the example

1. Install TesseractFlow in a virtual environment (`pip install -e .`).
2. Export an API key supported by LiteLLM (`export OPENROUTER_API_KEY=...`).
3. Execute the experiment:

   ```bash
   tesseract experiment run examples/code_review/experiment_config.yaml --output results.json --record-cache
   ```

4. Analyze and visualize the results:

   ```bash
   tesseract experiment analyze results.json --export optimal.yaml
   tesseract visualize pareto results.json --output pareto.png --budget 0.010
   ```

The configuration balances quality, cost, and latency across four binary variables: temperature, model, context window, and generation strategy. Use it as a template for your own repositories by replacing `sample_code_path` and rubric details.
