# TesseractFlow

**Systematic LLM workflow optimization using Taguchi Design of Experiments**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Version 0.1.0](https://img.shields.io/badge/version-0.1.0-green.svg)]()

---

## Why TesseractFlow?

**The Problem:** Optimizing LLM workflows is expensive and time-consuming. Testing 4 variables with 2 levels each requires 16 experiments (2⁴). With costly models and complex workflows, this becomes prohibitively expensive.

**The Solution:** TesseractFlow uses Taguchi Design of Experiments (DOE) to reduce 16 experiments to just 8, while still identifying which variables matter most. This means:

- **50% fewer API calls** - Test 4 variables in 8 experiments instead of 16
- **10x cost reduction** - Use cheap models (DeepSeek $0.69/M) for experimentation
- **Data-driven decisions** - Main effects analysis shows which variables contribute most to quality
- **Multi-objective optimization** - Balance quality, cost, and latency simultaneously

**Real-world example:** Our rubric.py code review experiment cost $0.40 and discovered that:
- Model choice impacts quality by 6.5% (Sonnet vs Haiku)
- Full context improves reviews by 4.7%
- Chain-of-thought actually reduces quality by 1.9%
- Temperature has minimal impact (1.0%)

---

## Key Features

- ✅ **Efficient Experimentation** - Taguchi L8 orthogonal arrays test 4-7 variables in just 8 runs
- ✅ **Quality Evaluation** - LLM-as-judge with customizable rubrics (0-100 point scale)
- ✅ **Multi-Objective Optimization** - Utility function balances quality, cost, and latency
- ✅ **Statistical Analysis** - Main effects show variable contributions with percentages
- ✅ **Pareto Visualization** - See quality vs cost trade-offs graphically
- ✅ **Provider Agnostic** - Works with any LiteLLM-supported provider (400+ models)
- ✅ **Rich CLI** - Beautiful terminal output with progress bars and colored tables
- ✅ **Evaluation Caching** - Reuse LLM evaluations across experiments
- ✅ **Resume Support** - Continue interrupted experiments from last checkpoint

---

## Installation

**Requirements:** Python 3.11+

```bash
# Clone the repository
git clone https://github.com/markramm/TesseractFlow.git
cd TesseractFlow

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e .
```

**Set up API keys:**

```bash
# For OpenRouter (recommended - access to 400+ models)
export OPENROUTER_API_KEY="your-key-here"

# Or for direct providers
export ANTHROPIC_API_KEY="your-key-here"
export OPENAI_API_KEY="your-key-here"
```

Verify installation:
```bash
tesseract --version
# Output: TesseractFlow 0.1.0
```

---

## Quick Start

### 1. Create an Experiment Configuration

Create `my_experiment.yaml`:

```yaml
name: "optimize_summarization"
workflow: "code_review"  # Example workflow (you can create your own)

# Define 4 variables to test (2 levels each)
variables:
  - name: "temperature"
    level_1: 0.3  # Deterministic
    level_2: 0.7  # Creative

  - name: "model"
    level_1: "openrouter/deepseek/deepseek-chat"  # Budget: $0.69/M
    level_2: "openrouter/anthropic/claude-haiku-4.5"  # Balanced: $3/M

  - name: "context_size"
    level_1: "file_only"     # Minimal context
    level_2: "full_module"   # Complete context

  - name: "generation_strategy"
    level_1: "standard"           # Direct prompting
    level_2: "chain_of_thought"   # Reasoning-based

# Utility function weights (how to trade off objectives)
utility_weights:
  quality: 1.0   # Most important
  cost: 0.1      # Moderately important
  time: 0.05     # Least important

# Workflow-specific configuration
workflow_config:
  rubric:
    clarity:
      description: "Is the output clear and understandable?"
      scale: "0-100 where 0=incomprehensible, 100=crystal clear"
      weight: 0.3

    accuracy:
      description: "Is the output factually accurate?"
      scale: "0-100 where 0=many errors, 100=fully accurate"
      weight: 0.4

    completeness:
      description: "Does the output address all requirements?"
      scale: "0-100 where 0=missing major parts, 100=comprehensive"
      weight: 0.3

  sample_code_path: "path/to/code.py"
  evaluator_model: "openrouter/anthropic/claude-haiku-4.5"
  evaluator_temperature: 0.3
```

### 2. Run the Experiment

```bash
# Preview what will run (dry-run mode)
tesseract experiment run my_experiment.yaml --dry-run

# Execute all 8 test configurations
tesseract experiment run my_experiment.yaml \
  --output results.json \
  --use-cache \
  --record-cache
```

You'll see beautiful progress output:
```
✓ Loaded experiment config: optimize_summarization
• Generating Taguchi L8 test configurations...
  Running experiment ━━━━━━━━━━━━━━━━━━━ 3/8 0:02:45
```

### 3. Analyze Results

```bash
# Show main effects analysis
tesseract analyze main-effects results.json

# Export optimal configuration
tesseract analyze main-effects results.json --export optimal.yaml
```

Output shows variable contributions:
```
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ Variable            ┃ Level 1    ┃ Level 2    ┃ Effect Size  ┃ Contribution %   ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ model               │   0.6562   │   0.6985   │    +0.0423   │      38.5%       │
│ context_size        │   0.6642   │   0.6955   │    +0.0313   │      48.2%       │
│ generation_strategy │   0.6842   │   0.6710   │    -0.0132   │       9.8%       │
│ temperature         │   0.6742   │   0.6812   │    +0.0070   │       3.5%       │
└─────────────────────┴────────────┴────────────┴──────────────┴──────────────────┘
```

**Key Insight:** Model and context_size contribute 86.7% of quality improvement!

### 4. Visualize Trade-offs

```bash
# Generate Pareto frontier chart
tesseract visualize pareto results.json --output pareto.png
```

This creates a chart showing which test configurations are Pareto-optimal (best quality for a given cost).

---

## Real-World Example

See `experiments/rubric_review_experiment.yaml` for a production-grade code review experiment that:
- Tested optimal settings for reviewing critical infrastructure code
- Cost $0.40 for complete L8 experiment
- Discovered Sonnet 4.5 provides 6.5% better reviews than Haiku
- Found that full module context improves quality by 4.7%
- Showed chain-of-thought reduces quality by 1.9% (surprising!)

Results documented in `experiments/FINDINGS.md`.

---

## CLI Reference

### Experiment Commands

```bash
# Run an experiment
tesseract experiment run CONFIG.yaml [OPTIONS]
  --output PATH          Save results to JSON file
  --dry-run              Preview test configurations without running
  --use-cache            Use cached evaluations
  --record-cache         Save evaluations to cache
  --resume               Continue from last checkpoint
  --verbose              Show detailed logging

# Validate configuration
tesseract experiment validate CONFIG.yaml

# Check status of running experiment
tesseract experiment status RESULTS.json
```

### Analysis Commands

```bash
# Main effects analysis
tesseract analyze main-effects RESULTS.json [OPTIONS]
  --export PATH          Export optimal config to YAML
  --show-config          Display recommended configuration (default: true)

# Quick summary
tesseract analyze summary RESULTS.json
```

### Visualization Commands

```bash
# Pareto frontier
tesseract visualize pareto RESULTS.json [OPTIONS]
  --output PATH          Save chart to file (default: pareto.png)
  --budget FLOAT         Highlight configs within budget
  --axes X Y             Choose axes (quality-cost, quality-latency, cost-latency)
```

---

## Project Structure

```
TesseractFlow/
├── tesseract_flow/          # Core framework
│   ├── core/                # Base classes, config, strategies
│   ├── experiments/         # Taguchi arrays, execution, analysis
│   ├── evaluation/          # LLM-as-judge rubric evaluator
│   ├── optimization/        # Utility functions, Pareto analysis
│   ├── workflows/           # Example workflows (code_review)
│   └── cli/                 # Command-line interface
├── examples/                # Example configurations
│   └── code_review/         # Code review workflow examples
├── experiments/             # Real experiment results
│   ├── rubric_review_experiment.yaml
│   ├── rubric_review_results.json
│   └── FINDINGS.md
├── docs/                    # Documentation
│   ├── openrouter-model-costs.md
│   ├── openrouter-model-capabilities.md
│   └── user-guide/
├── .claude/                 # Claude Code integration
│   └── skills/
│       └── tesseract-experiment-designer/  # AI-powered experiment design assistant
└── tests/                   # Test suite (80% coverage)
```

---

## Claude Code Integration

TesseractFlow includes a Claude Code skill for AI-assisted experiment design:

**`.claude/skills/tesseract-experiment-designer/`**

When using Claude Code in this repository, you can ask:

> "Design an experiment to optimize my summarization workflow. I want high quality but have a $0.50 budget."

Claude will:
1. Recommend a best-guess configuration based on your requirements
2. Design an L8 experiment to fill knowledge gaps
3. Estimate costs using OpenRouter pricing data
4. Generate a complete YAML configuration file

The skill references:
- `docs/openrouter-model-costs.md` - Pricing data for 15+ models
- `docs/openrouter-model-capabilities.md` - Performance benchmarks and optimal settings

---

## How It Works

### Taguchi Design of Experiments

Traditional grid search for 4 variables with 2 levels = 2⁴ = **16 experiments**

TesseractFlow uses Taguchi L8 orthogonal array = **8 experiments**

**L8 Array:**
```
Test #  Var1  Var2  Var3  Var4
  1      1     1     1     1
  2      1     1     2     2
  3      1     2     1     2
  4      1     2     2     1
  5      2     1     1     2
  6      2     1     2     1
  7      2     2     1     1
  8      2     2     2     2
```

Each variable appears 4 times at level 1 and 4 times at level 2, enabling unbiased main effects analysis.

### Main Effects Analysis

For each variable, TesseractFlow computes:
- **Average utility at level 1** (4 tests)
- **Average utility at level 2** (4 tests)
- **Effect size** = avg(level 2) - avg(level 1)
- **Contribution %** = (effect² / total variance) × 100

This tells you **which variables matter most** for improving your workflow.

### Utility Function

Combines multiple objectives into a single score:

```python
utility = (w_quality × quality) - (w_cost × cost) - (w_time × latency)
```

Configurable weights let you prioritize what matters for your use case.

---

## Documentation

- **[User Guide](docs/user-guide/)** - Getting started, configuration, interpreting results
- **[OpenRouter Models](docs/openrouter-model-costs.md)** - Cost tiers and pricing for 15+ models
- **[Model Capabilities](docs/openrouter-model-capabilities.md)** - Benchmarks and optimal settings
- **[API Reference](docs/api/)** - Core modules and extension points
- **[Examples](examples/)** - Ready-to-use experiment configurations

---

## Use Cases

### 1. Code Review Optimization
Test prompts, models, and context strategies to find optimal code review settings.

### 2. Summarization Quality
Experiment with temperature, context window, and generation strategies for summaries.

### 3. Data Extraction
Optimize structured output generation (JSON, YAML) with different models and temperatures.

### 4. Cost Reduction
Test cheap models (DeepSeek $0.69/M) vs expensive models (GPT-4 $30/M) to find best value.

### 5. Latency Optimization
Balance quality and response time for user-facing applications.

---

## Contributing

Contributions are welcome! Please:

1. **Open an issue** to discuss major changes
2. **Run tests** before submitting: `pytest --cov=tesseract_flow`
3. **Update docs** for new features
4. **Follow code style** established in `tesseract_flow/core/`

See `docs/development/setup.md` for development environment setup.

---

## Roadmap

### v0.2 (Next Release)
- [ ] Web dashboard for experiment visualization
- [ ] Parallel execution (8x speedup)
- [ ] Additional workflow examples (summarization, extraction)
- [ ] L16/L18 orthogonal arrays for more variables

### v0.3
- [ ] Human-in-the-loop (HITL) approval queue integration
- [ ] PostgreSQL backend for experiment history
- [ ] Experiment comparison tools
- [ ] Advanced evaluators (pairwise, ensemble)

### v1.0
- [ ] Hosted SaaS version
- [ ] Team collaboration features
- [ ] CI/CD integrations
- [ ] Workflow marketplace

---

## License

TesseractFlow is released under the [MIT License](LICENSE).

---

## Citation

If you use TesseractFlow in research or production, please cite:

```bibtex
@software{tesseractflow2025,
  title = {TesseractFlow: Multi-dimensional LLM Workflow Optimization},
  author = {Mark Ramm},
  year = {2025},
  version = {0.1.0},
  url = {https://github.com/markramm/TesseractFlow}
}
```

---

## Support

- **Issues:** [GitHub Issues](https://github.com/markramm/TesseractFlow/issues)
- **Discussions:** [GitHub Discussions](https://github.com/markramm/TesseractFlow/discussions)
- **Email:** mark.ramm@gmail.com

---

**Built with ❤️ using Taguchi DOE, LangGraph, and LiteLLM**
