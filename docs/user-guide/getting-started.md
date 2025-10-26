# Getting Started with TesseractFlow

This guide will walk you through your first LLM workflow optimization experiment using TesseractFlow.

## What You'll Learn

By the end of this guide, you'll be able to:
- Set up TesseractFlow in your environment
- Create an experiment configuration
- Run a Taguchi L8 experiment
- Analyze results to identify optimal settings
- Visualize quality vs cost trade-offs

## Prerequisites

- Python 3.11 or higher
- An API key for an LLM provider (OpenRouter recommended)
- Basic familiarity with YAML configuration files
- 10-15 minutes

## Installation

### 1. Clone and Install

```bash
git clone https://github.com/markramm/TesseractFlow.git
cd TesseractFlow

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install TesseractFlow
pip install -e .
```

### 2. Verify Installation

```bash
tesseract --version
```

Expected output:
```
TesseractFlow 0.1.0
```

### 3. Set Up API Keys

**For OpenRouter (Recommended):**

OpenRouter gives you access to 400+ models through a single API key. Sign up at https://openrouter.ai.

```bash
export OPENROUTER_API_KEY="your-key-here"
```

**For Direct Providers:**

```bash
# Anthropic (Claude)
export ANTHROPIC_API_KEY="your-key-here"

# OpenAI (GPT)
export OPENAI_API_KEY="your-key-here"
```

**Persist Keys (Optional):**

Add to your `~/.bashrc` or `~/.zshrc`:
```bash
echo 'export OPENROUTER_API_KEY="your-key-here"' >> ~/.bashrc
source ~/.bashrc
```

## Understanding the Basics

### What is Taguchi DOE?

Traditional grid search for 4 variables = **16 experiments**
TesseractFlow uses Taguchi L8 = **8 experiments** (50% reduction!)

### How Does It Work?

1. **Define Variables** - Choose 4 variables to test (e.g., model, temperature, context, strategy)
2. **Generate L8 Array** - TesseractFlow creates 8 optimal test configurations
3. **Run Experiments** - Each configuration is executed and evaluated
4. **Analyze Results** - Main effects analysis shows which variables matter most
5. **Identify Optimal** - Find the best configuration based on your priorities

### What Gets Optimized?

TesseractFlow balances three objectives:
- **Quality** - How good is the output? (0-1 score)
- **Cost** - How much did it cost? (USD)
- **Latency** - How long did it take? (seconds)

You control the trade-off with configurable weights.

## Your First Experiment

Let's optimize a code review workflow.

### Step 1: Create Configuration File

Create `my_first_experiment.yaml`:

```yaml
name: "my_first_code_review_experiment"
workflow: "code_review"

# 4 variables to test (2 levels each = L8 experiment)
variables:
  - name: "temperature"
    level_1: 0.3  # Deterministic
    level_2: 0.7  # Creative

  - name: "model"
    level_1: "openrouter/deepseek/deepseek-chat"  # Budget: $0.69/M tokens
    level_2: "openrouter/anthropic/claude-haiku-4.5"  # Quality: $3/M tokens

  - name: "context_size"
    level_1: "file_only"      # Just the target file
    level_2: "full_module"    # Include related files

  - name: "generation_strategy"
    level_1: "standard"            # Direct prompting
    level_2: "chain_of_thought"    # Step-by-step reasoning

# How to balance quality, cost, and time
utility_weights:
  quality: 1.0   # Most important (100%)
  cost: 0.1      # Moderately important (10%)
  time: 0.05     # Least important (5%)

# Define what "quality" means
workflow_config:
  rubric:
    correctness:
      description: |
        Does the review identify real issues?
        - Finds bugs and logic errors
        - Spots edge cases
        - No false positives
      scale: "0-100 where 0=missed everything, 100=found all issues"
      weight: 0.4  # 40% of quality score

    clarity:
      description: |
        Is the feedback clear and actionable?
        - Specific examples provided
        - Concrete suggestions
        - Easy to understand
      scale: "0-100 where 0=vague, 100=crystal clear"
      weight: 0.3  # 30% of quality score

    depth:
      description: |
        Does the review go beyond surface-level?
        - Architectural concerns
        - Performance implications
        - Maintainability issues
      scale: "0-100 where 0=superficial, 100=comprehensive"
      weight: 0.3  # 30% of quality score

  # Specify a real code file to review
  sample_code_path: "tesseract_flow/evaluation/rubric.py"

  # How to evaluate the reviews
  evaluator_model: "openrouter/anthropic/claude-haiku-4.5"
  evaluator_temperature: 0.3
```

### Step 2: Validate Configuration

Before running, check for errors:

```bash
tesseract experiment validate my_first_experiment.yaml
```

If valid, you'll see:
```
✓ Configuration is valid
• Variables: 4
• Rubric dimensions: 3
• Expected tests: 8
```

### Step 3: Preview Test Configurations (Dry Run)

See what will run without actually executing:

```bash
tesseract experiment run my_first_experiment.yaml --dry-run
```

Output shows all 8 test configurations:
```
Test #1: temperature=0.3, model=deepseek, context_size=file_only, generation_strategy=standard
Test #2: temperature=0.3, model=deepseek, context_size=full_module, generation_strategy=chain_of_thought
Test #3: temperature=0.3, model=haiku, context_size=file_only, generation_strategy=chain_of_thought
...
```

### Step 4: Run the Experiment

Execute all 8 tests:

```bash
tesseract experiment run my_first_experiment.yaml \
  --output results.json \
  --use-cache \
  --record-cache \
  --verbose
```

**Flags explained:**
- `--output results.json` - Save results to file
- `--use-cache` - Reuse cached evaluations (saves money)
- `--record-cache` - Save new evaluations to cache
- `--verbose` - Show detailed logging

You'll see progress:
```
✓ Loaded experiment config: my_first_code_review_experiment
• Generating Taguchi L8 test configurations...
  Running experiment ━━━━━━━━━━━━━━━━━━━ 3/8 0:02:45
```

**Estimated time:** 5-10 minutes (depending on models)
**Estimated cost:** $0.10-0.40 (depending on models and cache hits)

### Step 5: Analyze Results

#### Quick Summary

```bash
tesseract analyze summary results.json
```

Output:
```
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┓
┃ Metric             ┃             Value ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━┩
│ Tests completed    │               8/8 │
│ Utility range      │       0.63 – 0.75 │
│ Quality range      │       0.65 – 0.78 │
│ Cost range         │   $0.001 – $0.003 │
│ Latency range (s)  │       12.5 – 25.3 │
│ Best test          │   #5 utility=0.75 │
└────────────────────┴───────────────────┘
```

#### Main Effects Analysis

See which variables matter most:

```bash
tesseract analyze main-effects results.json
```

Output:
```
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ Variable            ┃ Level 1    ┃ Level 2    ┃ Effect Size  ┃ Contribution %   ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ model               │   0.6562   │   0.7185   │    +0.0623   │      45.2%       │
│ context_size        │   0.6742   │   0.7005   │    +0.0263   │      32.1%       │
│ generation_strategy │   0.6920   │   0.6827   │    -0.0093   │      15.3%       │
│ temperature         │   0.6842   │   0.6905   │    +0.0063   │       7.4%       │
└─────────────────────┴────────────┴────────────┴──────────────┴──────────────────┘

Optimal Configuration (Highest Utility)
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Variable            ┃ Recommended Value                    ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ context_size        │ full_module                          │
│ generation_strategy │ standard                             │
│ model               │ openrouter/anthropic/claude-haiku-4.5│
│ temperature         │ 0.7                                  │
└─────────────────────┴──────────────────────────────────────┘
```

**Key Insight:** Model and context_size contribute 77.3% of quality improvement!

#### Export Optimal Configuration

```bash
tesseract analyze main-effects results.json --export optimal.yaml
```

Creates `optimal.yaml` with recommended settings you can use in production.

### Step 6: Visualize Trade-offs

Generate Pareto frontier chart:

```bash
tesseract visualize pareto results.json --output pareto.png
```

This shows which configurations are Pareto-optimal (best quality for a given cost).

Open `pareto.png` to see the chart.

## Understanding Your Results

### Main Effects Table

Each row shows one variable's impact:

- **Level 1 Avg** - Average utility when variable is at level 1
- **Level 2 Avg** - Average utility when variable is at level 2
- **Effect Size** - Difference between levels (positive = level 2 better)
- **Contribution %** - How much this variable matters (sum = 100%)

**Example Interpretation:**

```
│ model  │  0.6562  │  0.7185  │  +0.0623  │  45.2%  │
```

- Upgrading from DeepSeek to Haiku improves utility by 0.0623
- Model choice accounts for 45.2% of quality variation
- This is the most important variable to get right!

### Utility Score

```
utility = (quality × 1.0) - (cost × 0.1) - (latency × 0.05)
```

Higher is better. Represents overall value considering all objectives.

### Pareto Frontier

Points on the frontier are "Pareto-optimal" - you can't improve one objective without hurting another.

- **On the frontier** - Efficient trade-off
- **Below the frontier** - Dominated by another config
- **Above the frontier** - Better than all tested configs (rare, may indicate noise)

## Next Steps

Now that you've run your first experiment, try:

1. **Customize the Rubric** - Add dimensions specific to your use case
2. **Test Different Variables** - Temperature, max_tokens, context strategies, etc.
3. **Adjust Utility Weights** - Prioritize cost if on tight budget
4. **Create Your Own Workflow** - Extend `BaseWorkflowService` for custom tasks

## Common Issues

### "API key not found"

**Solution:** Ensure environment variable is set:
```bash
echo $OPENROUTER_API_KEY  # Should print your key
```

If empty, re-export:
```bash
export OPENROUTER_API_KEY="your-key-here"
```

### "Experiment failed on test #3"

**Solution:** Check logs for specific error:
```bash
tesseract experiment run config.yaml --verbose
```

Common causes:
- Invalid model name
- Insufficient API credits
- Network issues (retry with `--resume`)

### Resume an Interrupted Experiment

If experiment stops mid-run:
```bash
tesseract experiment run config.yaml --output results.json --resume
```

TesseractFlow skips completed tests and continues from where it stopped.

### Reduce Costs

1. **Use cheap models** for workflow execution:
   ```yaml
   level_1: "openrouter/deepseek/deepseek-chat"  # $0.69/M
   ```

2. **Keep evaluator cheap**:
   ```yaml
   evaluator_model: "openrouter/anthropic/claude-haiku-4.5"  # $3/M
   ```

3. **Enable caching**:
   ```bash
   --use-cache --record-cache
   ```

4. **Test on small samples** first, then scale up

## Getting Help

- **Documentation:** [docs/](../../docs/)
- **Examples:** [examples/](../../examples/)
- **Issues:** [GitHub Issues](https://github.com/markramm/TesseractFlow/issues)
- **Discussions:** [GitHub Discussions](https://github.com/markramm/TesseractFlow/discussions)

## What's Next?

- **[Configuration Reference](configuration.md)** - All YAML options explained
- **[Interpreting Results](interpreting-results.md)** - Deep dive into analysis
- **[Creating Workflows](creating-workflows.md)** - Build custom workflows
- **[Advanced Techniques](advanced-techniques.md)** - L16 arrays, ensemble evaluation, HITL

---

**Congratulations!** You've completed your first TesseractFlow experiment. You now know how to systematically optimize LLM workflows with scientific rigor.
