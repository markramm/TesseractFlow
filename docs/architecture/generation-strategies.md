# Generation Strategies as Experimental Variables

**Date:** 2025-10-25
**Key Insight:** Verbalized Sampling is NOT a core feature—it's one generation strategy to test against standard prompting
**Impact:** Framework becomes more general-purpose, cleaner architecture

---

## The Insight

### ❌ **Old Thinking:** VS as Core Feature

```python
class BaseWorkflowService:
    def __init__(self, workflow_config):
        # VS is special, built into framework
        if workflow_config.verbalized_sampling.enabled:
            self.use_vs = True
            self.vs_k = workflow_config.vs_k
        else:
            self.use_vs = False

    async def generate(self, prompt):
        if self.use_vs:
            # Special VS path
            from verbalized_sampling import verbalize
            dist = verbalize(prompt, k=self.vs_k)
            return dist.sample()
        else:
            # Standard path
            return await self.model.ainvoke(prompt)
```

**Problems:**
- VS is hardcoded into framework
- Framework depends on VS library
- Can't easily add other generation strategies
- VS gets special treatment

---

### ✅ **New Thinking:** VS as Experimental Variable

```python
class BaseWorkflowService:
    async def generate(self, prompt):
        # Generation strategy is just a config variable
        strategy = self.config.generation_strategy

        if strategy == "verbalized_sampling":
            return await self._generate_vs(prompt)
        elif strategy == "chain_of_thought":
            return await self._generate_cot(prompt)
        elif strategy == "few_shot":
            return await self._generate_few_shot(prompt)
        else:
            # Standard prompting
            return await self._generate_standard(prompt)

    async def _generate_vs(self, prompt):
        """Optional strategy: Use Verbalized Sampling."""
        from verbalized_sampling import verbalize
        dist = verbalize(
            prompt=prompt,
            model=self.config.model,
            k=self.config.vs_k,
            tau=self.config.vs_tau
        )
        return dist.sample()
```

**Benefits:**
- ✅ VS is just another strategy (not special)
- ✅ Framework doesn't depend on VS library
- ✅ Easy to add new strategies
- ✅ All strategies tested the same way

---

## Taguchi Experiment with VS as Variable

### Example: Code Review Optimization

```yaml
# experiments/code_review_optimization.yaml
name: "code_review_optimization"
workflow: "code_review"

method:
  type: "taguchi_l8"

variables:
  # Variable 1: Temperature
  temperature:
    1: 0.3    # Conservative
    2: 0.7    # Creative

  # Variable 2: Model
  model:
    1: "deepseek/deepseek-coder-v2"
    2: "anthropic/claude-3.5-sonnet"

  # Variable 3: Context Size
  context_size:
    1: "file_only"
    2: "full_module"

  # Variable 4: Generation Strategy ⭐
  generation_strategy:
    1: "standard"              # Standard prompting
    2: "verbalized_sampling"   # VS with k=5
```

**VS is treated exactly like temperature or model** - just another variable to test!

---

### Taguchi Array (L8)

```
Test  Temp  Model      Context      Strategy
  1    0.3  deepseek   file_only    standard
  2    0.3  deepseek   full_module  verbalized_sampling
  3    0.3  claude     file_only    verbalized_sampling
  4    0.3  claude     full_module  standard
  5    0.7  deepseek   file_only    verbalized_sampling
  6    0.7  deepseek   full_module  standard
  7    0.7  claude     file_only    standard
  8    0.7  claude     full_module  verbalized_sampling
```

**Main Effects Analysis will show:** Does VS actually improve quality/cost/time?

**Possible outcomes:**
- VS contributes 40% → Keep it!
- VS contributes 5% → Not worth the cost
- Standard prompting actually better → Use that instead

---

## Generation Strategy Registry

### Pattern: Pluggable Strategies

```python
# generation_strategies.py

from typing import Protocol, Dict, Any

class GenerationStrategy(Protocol):
    """Protocol for generation strategies."""

    async def generate(
        self,
        prompt: str,
        model: LLMModel,
        config: Dict[str, Any]
    ) -> str:
        """Generate text using this strategy."""
        ...

# Built-in strategies
class StandardStrategy:
    """Standard prompting - direct LLM call."""

    async def generate(self, prompt, model, config):
        response = await model.ainvoke(prompt)
        return response.content

class VerbalizedSamplingStrategy:
    """Verbalized Sampling strategy."""

    async def generate(self, prompt, model, config):
        from verbalized_sampling import verbalize

        dist = verbalize(
            prompt=prompt,
            model=config["model"],
            provider=config.get("provider", "openrouter"),
            api_key=config["api_key"],
            k=config.get("vs_k", 5),
            tau=config.get("vs_tau", 0.10),
            temperature=config.get("temperature", 0.7)
        )

        return dist.sample()

class ChainOfThoughtStrategy:
    """Chain-of-thought prompting."""

    async def generate(self, prompt, model, config):
        # Add CoT instruction
        cot_prompt = f"{prompt}\n\nLet's think step by step:"

        response = await model.ainvoke(cot_prompt)
        return response.content

class FewShotStrategy:
    """Few-shot prompting with examples."""

    async def generate(self, prompt, model, config):
        examples = config.get("examples", [])

        few_shot_prompt = self._build_few_shot(prompt, examples)
        response = await model.ainvoke(few_shot_prompt)
        return response.content

    def _build_few_shot(self, prompt, examples):
        formatted = "\n\n".join([
            f"Example {i+1}:\nInput: {ex['input']}\nOutput: {ex['output']}"
            for i, ex in enumerate(examples)
        ])
        return f"{formatted}\n\nNow:\nInput: {prompt}\nOutput:"

# Strategy registry
GENERATION_STRATEGIES: Dict[str, GenerationStrategy] = {
    "standard": StandardStrategy(),
    "verbalized_sampling": VerbalizedSamplingStrategy(),
    "chain_of_thought": ChainOfThoughtStrategy(),
    "few_shot": FewShotStrategy(),
}

def get_strategy(name: str) -> GenerationStrategy:
    """Get strategy by name."""
    if name not in GENERATION_STRATEGIES:
        raise ValueError(f"Unknown strategy: {name}")
    return GENERATION_STRATEGIES[name]
```

---

## Workflow Configuration

### YAML Config with Strategy

```yaml
# workflows/defaults/code_review.yaml
name: "code_review"
version: "1.0"

models:
  analyzer:
    model: "deepseek/deepseek-coder-v2"
    temperature: 0.3

    # Generation strategy (variable to test)
    generation_strategy: "standard"  # or "verbalized_sampling"

    # Strategy-specific params (only used if strategy enabled)
    vs_k: 5
    vs_tau: 0.10

prompts:
  analyze: "code_review/analyze.jinja2"
```

### Workflow Implementation

```python
# workflows/code_review.py

class CodeReviewWorkflow(BaseWorkflow):
    async def execute(self, input: dict) -> dict:
        # Get configured strategy
        strategy_name = self.config.generation_strategy
        strategy = get_strategy(strategy_name)

        # Render prompt
        prompt = self.config.render_prompt("analyze", {
            "code": input["code"],
            "language": input["language"]
        })

        # Generate using configured strategy
        analysis = await strategy.generate(
            prompt=prompt,
            model=self.model,
            config=self.config.to_dict()  # Pass all config to strategy
        )

        return {"analysis": analysis}
```

**The workflow doesn't care which strategy** - it's configured externally!

---

## Experiment Configuration

### Testing Multiple Strategies

```yaml
# experiments/generation_strategy_comparison.yaml
name: "strategy_comparison"
workflow: "code_review"

method:
  type: "taguchi_l8"

variables:
  # Test different strategies
  generation_strategy:
    1: "standard"
    2: "verbalized_sampling"

  # Test different VS parameters (only matters when VS enabled)
  vs_k:
    1: 3
    2: 7

  # Other variables
  temperature:
    1: 0.3
    2: 0.7

  model:
    1: "deepseek/deepseek-coder-v2"
    2: "anthropic/claude-3.5-sonnet"
```

**Main effects analysis will tell you:**
- Which strategy works best
- Whether VS parameters matter (k=3 vs k=7)
- Whether strategy interacts with model choice

---

## Framework Benefits

### 1. No Hard Dependency on VS

```python
# llm_optimizer/core.py - NO import of verbalized_sampling

# VS is only imported if user chooses that strategy
# If user never tests VS, library is never imported

# This keeps framework lightweight
```

### 2. Easy to Add New Strategies

**User can add custom strategy:**

```python
# user_code.py

from llm_optimizer import GENERATION_STRATEGIES

class MyCustomStrategy:
    async def generate(self, prompt, model, config):
        # Custom logic
        return result

# Register custom strategy
GENERATION_STRATEGIES["my_custom"] = MyCustomStrategy()

# Now can use in experiments:
# generation_strategy: {1: "standard", 2: "my_custom"}
```

### 3. Framework Stays General-Purpose

**Framework provides:**
- ✅ Experiment design (Taguchi arrays)
- ✅ Workflow execution
- ✅ Quality evaluation
- ✅ Main effects analysis

**Framework does NOT provide:**
- ❌ Specific generation strategies (user's choice)
- ❌ Specific prompting techniques (user's choice)
- ❌ Specific models (user's choice)

**Framework is a TOOL, not a LIBRARY of techniques.**

---

## Comparison to Original Design

### Original (VS as Core Feature)

```yaml
# workflows/scene_draft.yaml
models:
  draft:
    model: "deepseek/deepseek-chat-v3.1"
    temperature: 0.9

    # VS is special, baked into framework
    verbalized_sampling:
      enabled: true
      k: 5
      tau: 0.10
```

**Problems:**
- Framework tightly coupled to VS
- VS gets special treatment
- Hard to compare VS to other strategies

---

### New (VS as Variable)

```yaml
# workflows/scene_draft.yaml
models:
  draft:
    model: "deepseek/deepseek-chat-v3.1"
    temperature: 0.9
    generation_strategy: "verbalized_sampling"  # Just a config value
    vs_k: 5
    vs_tau: 0.10
```

**Benefits:**
- Framework decoupled from VS
- VS is just another strategy
- Easy to A/B test: `generation_strategy: {1: "standard", 2: "verbalized_sampling"}`

---

## Example: Fiction Scene Drafting

### Experiment Design

```yaml
# experiments/scene_draft_optimization.yaml
name: "scene_draft_optimization"
workflow: "scene_draft"

method:
  type: "taguchi_l16"  # 5 variables, 2 levels

variables:
  # Variable 1: Context size
  context_size:
    1: "minimal"
    2: "full"

  # Variable 2: Temperature
  temperature:
    1: 0.5
    2: 0.9

  # Variable 3: Generation passes
  generation_passes:
    1: 1    # Single draft
    2: 3    # Parallel 3-draft merge

  # Variable 4: Caching
  caching:
    1: false
    2: true

  # Variable 5: Generation strategy ⭐
  generation_strategy:
    1: "standard"
    2: "verbalized_sampling"
```

**Result:** 16 experiments test whether VS improves quality/cost for fiction.

**Main effects might show:**
- Temperature: 35% contribution
- Context size: 25% contribution
- Generation strategy: 20% contribution ← **VS matters!**
- Generation passes: 15% contribution
- Caching: 5% contribution

**Insight:** VS is worth using (20% contribution), but temperature matters MORE (35%).

---

## Implementation Impact

### Framework Changes

**Before (VS as core feature):**
```
llm_optimizer/
├── core/
│   ├── workflow.py
│   ├── experiment.py
│   └── verbalized_sampling_integration.py  ← Tightly coupled
├── requirements.txt
│   └── verbalized-sampling>=0.1.0  ← Hard dependency
```

**After (VS as variable):**
```
llm_optimizer/
├── core/
│   ├── workflow.py
│   ├── experiment.py
│   └── generation_strategies/  ← Pluggable
│       ├── __init__.py
│       ├── standard.py
│       ├── chain_of_thought.py
│       └── few_shot.py
├── optional_strategies/  ← Optional dependencies
│   └── verbalized_sampling.py
├── requirements.txt
│   └── (no verbalized-sampling)  ← Not required
├── requirements-optional.txt
│   └── verbalized-sampling>=0.1.0  ← Optional
```

**Installation:**
```bash
# Minimal install
pip install llm-workflow-optimizer

# With VS support
pip install llm-workflow-optimizer[verbalized-sampling]

# With all optional strategies
pip install llm-workflow-optimizer[all-strategies]
```

---

## User Guide Example

### How to Test Verbalized Sampling

**Step 1: Install with VS support**
```bash
pip install llm-workflow-optimizer[verbalized-sampling]
```

**Step 2: Define experiment**
```yaml
# experiments/test_vs.yaml
name: "vs_evaluation"
workflow: "my_workflow"

variables:
  generation_strategy:
    1: "standard"              # Baseline
    2: "verbalized_sampling"   # Test VS

  # VS-specific parameters (only used when VS enabled)
  vs_k:
    1: 3
    2: 5
```

**Step 3: Run experiment**
```bash
llm-optimizer experiment run experiments/test_vs.yaml
```

**Step 4: Analyze results**
```bash
llm-optimizer experiment analyze results/vs_evaluation.json

# Output shows:
# generation_strategy contribution: 22%
#   - standard: avg utility 0.65
#   - verbalized_sampling: avg utility 0.82
#
# Recommendation: Use verbalized_sampling (26% better utility)
```

**VS is treated like any other variable** - no special treatment!

---

## Competitive Advantage

### vs DSPy

**DSPy:** Auto-optimizes prompts using their specific framework
- Must use DSPy pipeline structure
- Automated but opaque
- Hard to compare strategies manually

**Us:** User tests strategies explicitly
- Works with any workflow
- Transparent A/B testing
- Clear which strategy wins and why

---

### vs LangSmith

**LangSmith:** Manual A/B testing
- Run config A, run config B, compare
- No systematic experiment design

**Us:** Taguchi experiments test multiple variables efficiently
- 8 experiments test 4 variables
- Main effects show which variables matter
- Optimal config identified automatically

---

## Benefits Summary

### ✅ Cleaner Architecture
- Framework doesn't depend on specific techniques
- Strategies are pluggable
- Easy to extend

### ✅ Better Science
- VS is tested, not assumed
- Can compare VS to other strategies
- Data-driven decision (not hype-driven)

### ✅ User Flexibility
- Users choose which strategies to test
- Users can add custom strategies
- Framework doesn't impose techniques

### ✅ Lighter Weight
- Core framework has fewer dependencies
- Optional strategies installed separately
- Faster installation for basic use

---

## Updated Spec Changes

### Remove from Core Framework

❌ **Remove:**
- Hardcoded VS integration
- VS-specific YAML config
- VS as first-class feature

✅ **Add:**
- Generation strategy registry
- Strategy plugin system
- VS as optional strategy (separate package)

### New YAML Structure

```yaml
# workflows/my_workflow.yaml
models:
  my_model:
    model: "deepseek/deepseek-chat-v3.1"
    temperature: 0.9

    # Generation strategy (variable to test)
    generation_strategy: "standard"

    # Strategy-specific params
    # (only used if relevant strategy enabled)
    vs_k: 5
    vs_tau: 0.10
    cot_steps: 3
    few_shot_examples: []
```

### Experiment YAML

```yaml
# experiments/my_experiment.yaml
variables:
  generation_strategy:
    1: "standard"
    2: "verbalized_sampling"
    # Could also test:
    # 2: "chain_of_thought"
    # 2: "few_shot"
```

---

## Next Steps

### Week 1: Refactor Spec

Update `llm-workflow-optimizer-spec.md`:
- Remove VS as core feature
- Add generation strategy registry
- Update examples to show VS as variable

### Week 2: Prototype Strategy System

```python
# Minimal implementation
strategies = {
    "standard": lambda prompt, model: model.invoke(prompt),
    "vs": lambda prompt, model: verbalize(...).sample(),
}

strategy_name = config.generation_strategy
result = await strategies[strategy_name](prompt, model)
```

### Week 3: Test with Real Experiment

Run experiment comparing strategies:
- Test 1-4: standard
- Test 5-8: verbalized_sampling
- Compare quality/cost/time
- Validate main effects analysis works

---

## Conclusion

**This is MUCH better than VS as core feature because:**

1. ✅ **Framework stays general-purpose** - Not tied to specific technique
2. ✅ **VS is validated, not assumed** - Science-based decision
3. ✅ **Easy to extend** - Users can add strategies
4. ✅ **Lighter dependencies** - VS is optional
5. ✅ **Better positioning** - Framework, not library

**VS becomes:**
- Not a feature to promote
- But a hypothesis to test
- Just like temperature or model choice
- Data determines if it's worth using

**Framework becomes:**
- A tool for testing hypotheses
- Not prescriptive about techniques
- Agnostic to generation strategies
- Focused on systematic optimization

This is the right abstraction! 🎯
