# TesseractFlow

**Multi-dimensional LLM workflow optimization using Taguchi Design of Experiments**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Status: Alpha](https://img.shields.io/badge/status-alpha-orange.svg)]()

---

## Overview

TesseractFlow is a **structured alternative to LLM fine-tuning** for performance optimization. Instead of expensive, brittle fine-tuning that becomes obsolete as models evolve, TesseractFlow helps you systematically optimize workflows through prompt engineering, context design, model selection, and generation strategies.

### Why TesseractFlow?

**The Problem with Fine-Tuning:**
- Expensive ($1000s per training run)
- Brittle (breaks with model updates)
- Slow (days to weeks)
- Vendor lock-in (tied to specific model versions)

**The TesseractFlow Approach:**
- Optimize prompts, context, and strategies (not model weights)
- Works with any LLM provider (OpenRouter, Anthropic, OpenAI, etc.)
- Results in hours, not weeks
- Continuous optimization as models evolve
- Data-driven decisions via Taguchi DOE

### Core Capabilities

1. **Efficient Experimentation** - Test 4-7 variables with just 8 experiments (Taguchi L8 array)
2. **Multi-Objective Optimization** - Balance Quality, Cost, and Latency simultaneously
3. **Pareto Frontier Analysis** - Visualize trade-offs between competing objectives
4. **Generation Strategy Testing** - Compare standard prompting, Chain-of-Thought, Verbalized Sampling, etc.
5. **Pluggable Architecture** - Works with LangGraph, custom workflows, any LLM provider

---

## Quick Start

### Installation

```bash
pip install tesseract-flow
```

**With optional strategies:**
```bash
pip install tesseract-flow[verbalized-sampling]  # Adds VS support
pip install tesseract-flow[all]                  # All optional strategies
```

### Basic Usage

**1. Define your workflow:**

```python
from tesseract_flow import BaseWorkflowService
from pydantic import BaseModel

class CodeReviewInput(BaseModel):
    code: str
    language: str

class CodeReviewOutput(BaseModel):
    issues: List[Dict[str, str]]
    suggestions: List[str]

class CodeReviewWorkflow(BaseWorkflowService[CodeReviewInput, CodeReviewOutput]):
    def _build_workflow(self) -> StateGraph:
        # Define workflow logic using LangGraph
        graph = StateGraph()
        graph.add_node("analyze", self._analyze_code)
        graph.add_node("suggest", self._generate_suggestions)
        graph.add_edge("analyze", "suggest")
        return graph.compile()
```

**2. Configure experiment:**

```yaml
# experiments/optimize_code_review.yaml
name: "code_review_optimization"
workflow: "code_review"

method:
  type: "taguchi_l8"

variables:
  temperature: {1: 0.3, 2: 0.7}
  model: {1: "deepseek/deepseek-coder-v2", 2: "anthropic/claude-3.5-sonnet"}
  context_size: {1: "file_only", 2: "full_module"}
  generation_strategy: {1: "standard", 2: "verbalized_sampling"}

utility_weights:
  quality: 0.6
  cost: 0.3
  time: 0.1
```

**3. Run experiment:**

```bash
tesseract experiment run experiments/optimize_code_review.yaml
```

**4. Analyze results:**

```
Main Effects Analysis:
  context_size: 45% contribution (full_module >> file_only)
  model: 22% contribution (claude > deepseek)
  temperature: 18% contribution (0.7 > 0.3)
  generation_strategy: 15% contribution (verbalized_sampling > standard)

Optimal Configuration:
  temperature: 0.7
  model: anthropic/claude-3.5-sonnet
  context_size: full_module
  generation_strategy: verbalized_sampling

Pareto Frontier (Quality vs Cost):
  Config 8: Quality 0.88, Cost $0.25 ⭐ (Highest quality)
  Config 4: Quality 0.82, Cost $0.12 ⭐ (Best balance)
  Config 1: Quality 0.72, Cost $0.02 ⭐ (Lowest cost)
```

---

## Key Concepts

### Taguchi Design of Experiments

Traditional optimization requires testing every combination of variables (full factorial):
- 4 variables × 2 levels = 2^4 = **16 experiments**

TesseractFlow uses Taguchi orthogonal arrays:
- 4 variables × 2 levels = **8 experiments** (L8 array)
- **50% reduction** in experiments
- Still identifies which variables matter most (main effects)

### Multi-Objective Optimization

Most LLM optimization focuses on quality alone. TesseractFlow optimizes:
- **Quality** - Task-specific metrics (accuracy, coherence, etc.)
- **Cost** - API costs in USD
- **Time** - Latency in milliseconds

**Utility Function:**
```
utility = (w_quality × quality) - (w_cost × normalized_cost) - (w_time × normalized_time)
```

**Pareto Frontier:**
Visualize trade-offs between quality and cost. Choose configurations based on your budget and requirements.

### Generation Strategies as Variables

TesseractFlow treats prompting techniques as **experimental variables to test**, not assumptions:

- **Standard Prompting** - Direct LLM call
- **Chain-of-Thought** - "Let's think step by step..."
- **Few-Shot** - Examples before the task
- **Verbalized Sampling** - Sample from probability distribution (optional)

Test which strategy actually improves your task:
```yaml
variables:
  generation_strategy:
    1: "standard"
    2: "verbalized_sampling"
```

Main effects analysis tells you if the strategy contributes to quality improvement.

### Workflows as Boundaries (HITL)

Human-in-the-loop (HITL) occurs **between workflows**, not within them:

```
Workflow 1: Generate Draft  →  Database (Approval Queue)  →  Workflow 2: Apply Feedback
  (10-60 seconds)              (Human reviews async)           (10-60 seconds)
```

**Benefits:**
- No complex orchestration (Temporal, checkpointing)
- Simple synchronous workflows
- Human reviews at their own pace
- Works with any workflow framework

---

## Architecture

### Technology Stack

- **Python 3.11+** - Core framework
- **LangGraph** - Workflow orchestration
- **LiteLLM** - Universal LLM provider gateway
- **FastAPI** - REST API for workflows and approvals
- **PostgreSQL** - Results, experiments, approval queue
- **Langfuse** - Observability and experiment tracking

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    CLI / API Interface                       │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                  Experiment Orchestrator                     │
│  - Taguchi array generation (L8, L16, L18)                  │
│  - Test execution across configurations                      │
│  - Main effects analysis                                     │
│  - Pareto frontier computation                               │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                   Workflow Executor                          │
│  - BaseWorkflowService[TInput, TOutput]                     │
│  - Generation strategy selection                            │
│  - LangGraph integration                                     │
└─────────┬─────────────────┴─────────────────┬───────────────┘
          │                                   │
┌─────────▼──────────────┐       ┌───────────▼──────────────┐
│  Generation Strategies │       │   Quality Evaluator      │
│  - Standard            │       │   - Rubric-based         │
│  - Chain-of-Thought    │       │   - Pairwise A/B         │
│  - Few-Shot            │       │   - Ensemble judges      │
│  - Verbalized Sampling │       │   - Custom evaluators    │
└─────────┬──────────────┘       └───────────┬──────────────┘
          │                                   │
┌─────────▼───────────────────────────────────▼───────────────┐
│              LLM Provider Gateway (LiteLLM)                  │
│  OpenRouter • Anthropic • OpenAI • DeepSeek • Azure         │
└──────────────────────────────────────────────────────────────┘
```

---

## Comparison to Alternatives

### vs Fine-Tuning

| Fine-Tuning | TesseractFlow |
|-------------|---------------|
| $1000s per run | $10s for experiments |
| Days to weeks | Hours |
| Brittle (model version locked) | Works with any model |
| Vendor lock-in | Provider agnostic |
| Opaque (hard to debug) | Transparent (see what works) |

### vs DSPy

| DSPy | TesseractFlow |
|------|---------------|
| Auto-optimizes prompts | User tests variables explicitly |
| Must use DSPy pipeline | Works with any workflow |
| Opaque optimization | Transparent main effects |
| Grid search (slow) | Taguchi (efficient) |

### vs LangSmith

| LangSmith | TesseractFlow |
|-----------|---------------|
| Manual A/B testing | Systematic DOE |
| No experiment design | Taguchi arrays |
| Observability focus | Optimization focus |
| Run A vs B, compare | 8 tests, 4 variables |

**TesseractFlow integrates with LangSmith/Langfuse for observability.**

---

## Use Cases

### 1. Code Review Optimization
Test variables:
- Temperature (conservative vs creative)
- Model (DeepSeek vs Claude vs GPT-4)
- Context size (file vs module vs full codebase)
- Generation strategy (standard vs CoT)

**Result:** Find configuration that maximizes issue detection while minimizing false positives and cost.

### 2. Creative Writing (Fiction Scenes)
Test variables:
- Temperature
- Model
- Context (minimal vs full story context)
- Generation strategy (standard vs Verbalized Sampling)

**Result:** Find configuration that maximizes diversity and quality while staying within budget.

### 3. Documentation Generation
Test variables:
- Model (technical models vs general models)
- Context size
- Few-shot examples (0 vs 3 vs 5)
- Output format (markdown vs restructured text)

**Result:** Find configuration that produces clear, accurate documentation efficiently.

### 4. Customer Support Response Generation
Test variables:
- Temperature
- Model
- Context (ticket only vs customer history)
- Generation strategy (standard vs few-shot)

**Result:** Balance quality (customer satisfaction) with cost and response time.

---

## Roadmap

### Phase 1: MVP (Weeks 1-8)
- ✅ Core workflow framework
- ✅ Taguchi L8 experiments
- ✅ Rubric-based evaluation
- ✅ Pareto frontier visualization
- ✅ LiteLLM provider abstraction
- ✅ Langfuse integration

### Phase 2: Advanced Features (Weeks 9-16)
- ⏳ Pairwise A/B evaluation
- ⏳ Judge ensembles
- ⏳ L16/L18 orthogonal arrays
- ⏳ Web UI for approval queue
- ⏳ TruLens evaluator integration

### Phase 3: Platform (Weeks 17-24)
- 📋 Multi-user support
- 📋 Experiment history and comparison
- 📋 Custom strategy plugins
- 📋 Advanced visualizations

---

## Contributing

TesseractFlow is in early development. We welcome:

- **Use cases and feedback** - What workflows are you optimizing?
- **Bug reports** - Found an issue? Open a GitHub issue.
- **Feature requests** - What would make TesseractFlow more useful?
- **Code contributions** - PRs welcome! See `CONTRIBUTING.md`

---

## Documentation

- [Architecture Overview](docs/architecture/unified-spec.md)
- [Simplified HITL Pattern](docs/architecture/simplified-hitl.md)
- [Generation Strategies](docs/architecture/generation-strategies.md)
- [Examples](examples/)

---

## License

MIT License - see [LICENSE](LICENSE) for details

---

## Citation

If you use TesseractFlow in your research or product, please cite:

```bibtex
@software{tesseractflow2025,
  title = {TesseractFlow: Multi-dimensional LLM Workflow Optimization},
  author = {Ramm, Mark},
  year = {2025},
  url = {https://github.com/markramm/TesseractFlow}
}
```

---

## Acknowledgments

- **Taguchi Methods** - Genichi Taguchi's Design of Experiments
- **LangGraph** - Workflow orchestration framework
- **Verbalized Sampling** - Research from CHATS Lab (arXiv:2510.01171v3)
- **LiteLLM** - Universal LLM provider abstraction

---

**TesseractFlow** - Navigate the quality-cost-time manifold
