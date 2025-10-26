# Quickstart Guide: LLM Workflow Optimizer MVP

**Feature**: 001-mvp-optimizer | **Date**: 2025-10-25

This guide walks through running your first Taguchi experiment to optimize an LLM workflow.

---

## Prerequisites

- Python 3.11+
- API key for at least one LLM provider (OpenRouter, Anthropic, or OpenAI)
- TesseractFlow installed: `pip install tesseract-flow`

---

## Scenario: Optimize Code Review Workflow

**Goal:** Find the best configuration of 4 variables (temperature, model, context size, generation strategy) to maximize code review quality while minimizing cost.

**Expected Time:** ~15 minutes for 8 experiments

---

## Step 1: Create Experiment Configuration

Create `experiments/code_review.yaml`:

```yaml
name: "code_review_optimization"
workflow: "code_review"

variables:
  # Variable 1: Temperature
  temperature:
    level_1: 0.3  # Conservative (more deterministic)
    level_2: 0.7  # Creative (more varied)

  # Variable 2: Model
  model:
    level_1: "openai/gpt-4"
    level_2: "anthropic/claude-3.5-sonnet"

  # Variable 3: Context Size
  context_size:
    level_1: "file_only"     # Just the file being reviewed
    level_2: "full_module"   # Entire module for context

  # Variable 4: Generation Strategy
  generation_strategy:
    level_1: "standard"          # Direct prompting
    level_2: "chain_of_thought"  # CoT reasoning

# How to balance quality, cost, time
utility_weights:
  quality: 1.0   # Weight for quality score
  cost: 0.1      # Penalty for higher cost
  time: 0.05     # Penalty for longer latency

# Quality evaluation rubric
workflow_config:
  rubric:
    clarity:
      description: "Is the code review clear and actionable?"
      scale: "1-10 where 1=vague, 10=crystal clear"
    accuracy:
      description: "Are identified issues actually problems?"
      scale: "1-10 where 1=many false positives, 10=all accurate"
    completeness:
      description: "Does review cover important aspects?"
      scale: "1-10 where 1=superficial, 10=comprehensive"
    usefulness:
      description: "Are suggestions practical and helpful?"
      scale: "1-10 where 1=not useful, 10=highly actionable"

  # Sample code to review (in real use, would be dynamic)
  sample_code_path: "examples/code_review/sample_code/example1.py"

# For reproducibility
seed: 42
```

---

## Step 2: Set API Keys

```bash
# Option 1: Environment variable
export OPENROUTER_API_KEY="your-key-here"

# Option 2: Config file
echo "OPENROUTER_API_KEY=your-key-here" > .env
```

---

## Step 3: Run the Experiment

```bash
tesseract experiment run experiments/code_review.yaml -o results.json -v
```

**Expected Output:**

```
✓ Loaded experiment config: code_review_optimization
✓ Generated 8 test configurations from L8 array
✓ Validated workflow: code_review

Test Configurations:
  1. temp=0.3, model=gpt-4, context=file_only, strategy=standard
  2. temp=0.3, model=gpt-4, context=full_module, strategy=chain_of_thought
  3. temp=0.3, model=claude, context=file_only, strategy=chain_of_thought
  4. temp=0.3, model=claude, context=full_module, strategy=standard
  5. temp=0.7, model=gpt-4, context=file_only, strategy=chain_of_thought
  6. temp=0.7, model=gpt-4, context=full_module, strategy=standard
  7. temp=0.7, model=claude, context=file_only, strategy=standard
  8. temp=0.7, model=claude, context=full_module, strategy=chain_of_thought

Running experiments...

✓ Test 1/8 [████████████████████] 2.3s
   Quality: 0.75 | Cost: $0.004 | Latency: 2.3s | Utility: 0.71

✓ Test 2/8 [████████████████████] 3.1s
   Quality: 0.82 | Cost: $0.006 | Latency: 3.1s | Utility: 0.79

✓ Test 3/8 [████████████████████] 2.8s
   Quality: 0.88 | Cost: $0.008 | Latency: 2.8s | Utility: 0.84

✓ Test 4/8 [████████████████████] 2.1s
   Quality: 0.78 | Cost: $0.005 | Latency: 2.1s | Utility: 0.74

✓ Test 5/8 [████████████████████] 3.4s
   Quality: 0.85 | Cost: $0.007 | Latency: 3.4s | Utility: 0.81

✓ Test 6/8 [████████████████████] 2.2s
   Quality: 0.80 | Cost: $0.005 | Latency: 2.2s | Utility: 0.76

✓ Test 7/8 [████████████████████] 1.9s
   Quality: 0.72 | Cost: $0.003 | Latency: 1.9s | Utility: 0.69

✓ Test 8/8 [████████████████████] 3.6s
   Quality: 0.92 | Cost: $0.012 | Latency: 3.6s | Utility: 0.87

All tests completed in 21.4s
✓ Results saved to: results.json

Summary:
  Tests: 8/8 completed
  Quality range: 0.72 - 0.92
  Cost range: $0.003 - $0.012
  Utility range: 0.69 - 0.87
  Best utility: Test #8 (0.87)

Next steps:
  tesseract analyze results.json
  tesseract visualize pareto results.json
```

---

## Step 4: Analyze Results

```bash
tesseract analyze results.json --show-chart
```

**Output:**

```
Main Effects Analysis
═══════════════════════════════════════════════════════

Variable            Effect    Level 1   Level 2   Contribution
──────────────────────────────────────────────────────────────
context_size        +0.140    0.702     0.842     38.5%
model               +0.102    0.728     0.830     25.7%
temperature         +0.085    0.735     0.820     17.8%
generation_strategy +0.075    0.745     0.820     13.9%
──────────────────────────────────────────────────────────────
Total                                              95.9%
Unexplained variance                                4.1%

KEY INSIGHTS:

1. Context Size MATTERS MOST (38.5%)
   → Including full module context improves utility by 0.140
   → This is the biggest win

2. Model Choice is Second (25.7%)
   → Claude-3.5-Sonnet outperforms GPT-4 by 0.102
   → Significant but less than context

3. Temperature has Moderate Impact (17.8%)
   → Higher temperature (0.7) slightly better
   → Worth testing but not critical

4. Strategy has Smallest Effect (13.9%)
   → Chain-of-thought helps but minimally
   → Consider standard for cost savings

Optimal Configuration:
  temperature: 0.7 (level 2) ✓
  model: anthropic/claude-3.5-sonnet (level 2) ✓
  context_size: full_module (level 2) ✓
  generation_strategy: chain_of_thought (level 2) ✓

Expected Performance:
  Quality: 0.92 (±0.03)
  Cost: $0.012 per review
  Latency: 3.6s per review
  Utility: 0.87

This configuration appeared in test #8.

RECOMMENDATIONS:

✓ Deploy: Use full_module context (biggest impact)
✓ Deploy: Use claude-3.5-sonnet (good quality/cost ratio)
? Consider: Standard strategy instead of CoT (13.9% vs cost)
? Test: Temperature 0.5 as middle ground (not in L8 array)
```

---

## Step 5: Visualize Trade-offs

```bash
tesseract visualize pareto results.json -o pareto.png --budget 0.01
```

**Generated Chart Description:**

Scatter plot showing:
- **X-axis:** Cost (USD)
- **Y-axis:** Quality (0-1 scale)
- **Bubble size:** Latency
- **Colors:**
  - Blue = Pareto-optimal (not dominated)
  - Gray = Dominated (inferior to another config)
- **Red line:** Budget threshold at $0.01

**Pareto Frontier Points:**

```
Pareto-Optimal Configurations:

  Test #7: quality=0.72, cost=$0.003, latency=1.9s
  → BEST for tight budgets
  → Config: temp=0.7, model=gpt-4, context=file_only, strategy=standard

  Test #3: quality=0.88, cost=$0.008, latency=2.8s
  → BALANCED quality/cost
  → Config: temp=0.3, model=claude, context=file_only, strategy=chain_of_thought

  Test #8: quality=0.92, cost=$0.012, latency=3.6s
  → BEST quality (if budget allows)
  → Config: temp=0.7, model=claude, context=full_module, strategy=chain_of_thought

Within $0.01 budget:
  → Recommend Test #3 (quality=0.88, cost=$0.008)
  → Avoids Test #8 which exceeds budget
```

---

## Step 6: Export Optimal Config

```bash
tesseract analyze results.json --export optimal_config.yaml
```

**Generated `optimal_config.yaml`:**

```yaml
# Optimal configuration from experiment: code_review_optimization
# Test #8: utility=0.87, quality=0.92, cost=$0.012, latency=3.6s

temperature: 0.7
model: "anthropic/claude-3.5-sonnet"
context_size: "full_module"
generation_strategy: "chain_of_thought"

# Metadata
experiment_id: "exp_20251025_143022"
test_number: 8
date_generated: "2025-10-25T14:32:15Z"

# Expected performance
expected_quality: 0.92
expected_cost_per_run: 0.012
expected_latency_ms: 3600

# Use this config in your code review workflow
```

---

## Step 7: Deploy Optimal Configuration

Update your production code review workflow:

```python
# workflows/code_review.py

from tesseract_flow.workflows import CodeReviewWorkflow

# Load optimal config
workflow = CodeReviewWorkflow.from_yaml("optimal_config.yaml")

# Use in production
result = await workflow.execute({
    "code": open("src/my_module.py").read(),
    "context": "full_module"  # As recommended by experiment
})

print(f"Review: {result.review}")
print(f"Quality score: {result.quality_score}")
```

---

## What Just Happened?

### The Experiment

1. **Taguchi L8 Design:** Tested 4 variables with 2 levels each = 8 experiments (not 16!)
2. **Systematic Testing:** L8 array ensures each variable effect can be measured independently
3. **Multi-Objective:** Optimized quality, cost, AND latency simultaneously

### The Analysis

1. **Main Effects:** Identified context_size as the biggest contributor (38.5%)
2. **Optimal Config:** Found best combination (Test #8)
3. **Pareto Frontier:** Revealed quality/cost trade-offs for budget decisions

### The Savings

- **Time:** 8 experiments instead of 16 (50% reduction)
- **Cost:** Avoided testing all 16 combinations
- **Insights:** Clear data on what matters most (context > model > temp > strategy)

---

## Next Steps

### Validate the Results

Run a confirmation experiment with the optimal config:

```bash
tesseract experiment run optimal_config.yaml --repeat 5
```

This runs the optimal config 5 times to verify consistency.

### Test New Hypotheses

Based on results, you might want to:

1. **Test intermediate temperatures** (0.5 wasn't in L8)
2. **Add new variables** (e.g., max_tokens, prompt_template)
3. **Test on different code samples** (is full_module always best?)

### Iterate

```yaml
# experiments/code_review_v2.yaml

# Based on learnings from v1:
# - Lock in: full_module context (clear winner)
# - Test: temperature range 0.4-0.8 (refine)
# - Test: prompt variations (new variable)
# - Skip: generation_strategy (minimal impact)

variables:
  temperature:
    level_1: 0.4
    level_2: 0.8

  model:
    level_1: "anthropic/claude-3.5-sonnet"  # Winner from v1
    level_2: "anthropic/claude-3-opus"      # Test even better?

  prompt_template:
    level_1: "standard_review"
    level_2: "security_focused"

  max_output_tokens:
    level_1: 500
    level_2: 1000
```

---

## Common Patterns

### Pattern 1: Cost-Constrained Optimization

When budget is tight, use Pareto chart to find best quality within budget:

```bash
# Only show configs under $0.005
tesseract visualize pareto results.json --budget 0.005
```

### Pattern 2: Rapid Iteration

Start with L8 (4 variables), refine with another L8:

```
Iteration 1 (L8): Broad search
  → Identifies: context_size matters most

Iteration 2 (L8): Refine top variables
  → Tests: different context strategies

Iteration 3 (Manual): Fine-tune winner
  → Confirmation runs
```

### Pattern 3: Multi-Workflow Optimization

Run same experiment across different workflows:

```bash
# Code review
tesseract experiment run experiments/code_review.yaml -o code_review_results.json

# Documentation generation
tesseract experiment run experiments/doc_generation.yaml -o doc_gen_results.json

# Compare which variables generalize
tesseract experiment compare code_review_results.json doc_gen_results.json
```

---

## Troubleshooting

### "Experiment taking too long"

- Check API rate limits (add delays if needed)
- Use smaller sample_code
- Enable caching for repeated prompts

### "Quality scores all very similar"

- Variables may not matter for this workflow
- Try more impactful variables (model, prompt structure)
- Check if rubric is too coarse-grained

### "Cost estimates seem wrong"

- Verify LiteLLM is tracking tokens correctly
- Check pricing for your specific provider
- Ensure streaming is disabled (affects cost tracking)

---

## Tips for Success

1. **Start Simple:** 4 variables for your first experiment
2. **Choose Impactful Variables:** Model, temperature, context size usually matter
3. **Use Clear Rubrics:** Specific dimensions (clarity, accuracy) beat vague "quality"
4. **Validate Winners:** Run confirmation tests before deploying
5. **Iterate:** L8 → analyze → refine → L8 again

---

## What's Next?

**After MVP:**
- Database persistence (track experiments over time)
- Comparison tools (A/B test old vs new configs)
- L16/L18 arrays (test more variables or interactions)
- Automated config deployment

**For Now:**
- Run experiments on your actual workflows
- Share results (main effects charts are great for blog posts!)
- Build intuition about what variables matter in LLM workflows

---

Ready to optimize your first workflow? Run the example above or create your own experiment config!
