# LLM Workflow Optimizer - Unified Specification

**Date:** 2025-10-25
**Version:** 2.0 (Synthesis)
**Status:** Architecture Complete, Ready for Implementation

---

## Executive Summary

This specification synthesizes insights from:
1. Original workflow optimizer design
2. Simplified HITL architecture (workflows-as-boundaries)
3. Generation strategies as experimental variables
4. ChatGPT's DOE best practices

**Result:** A general-purpose LLM workflow optimization framework that:
- Tests multiple variables efficiently using Taguchi DOE
- Supports human-in-the-loop without complex orchestration
- Treats prompting techniques as experimental variables, not assumptions
- Provides multi-objective optimization (Quality + Cost + Time)
- Integrates with existing observability platforms

---

## Core Philosophy

### 1. Workflows as Boundaries

**Pattern:** Human-in-the-loop occurs BETWEEN workflows, not within them.

```
Workflow 1: Generate Draft          → Completes in 10-60 seconds
    ↓
Database: Approval Queue           → Asynchronous human review
    ↓
Workflow 2: Apply Feedback         → Completes in 10-60 seconds
```

**Benefits:**
- ✅ No pause/resume needed
- ✅ No complex orchestration (Temporal)
- ✅ Simple synchronous workflows
- ✅ Works with any framework

### 2. Generation Strategies as Variables

**Pattern:** Prompting techniques (VS, CoT, few-shot) are experimental variables to test, not core features.

```yaml
variables:
  generation_strategy:
    1: "standard"              # Baseline
    2: "verbalized_sampling"   # Test if VS improves quality
```

**Benefits:**
- ✅ Framework stays general-purpose
- ✅ Techniques are validated, not assumed
- ✅ Easy to add custom strategies
- ✅ Lighter dependencies (strategies are optional)

### 3. Multi-Objective Optimization

**Pattern:** Optimize for Quality AND Cost AND Time simultaneously.

**Utility Function:**
```python
utility = (w_quality * quality_score) - (w_cost * normalized_cost) - (w_time * normalized_time)
```

**Pareto Frontier:** Visual representation of non-dominated solutions (Quality vs Cost).

**Benefits:**
- ✅ Find best trade-offs, not just "best quality"
- ✅ Business constraints matter (cost budgets)
- ✅ See all viable options on Pareto curve

---

## Architecture Overview

### Technology Stack

**Core Framework:**
- **Python 3.11+** - VS integration, Taguchi math (SciPy/NumPy)
- **FastAPI** - REST API for workflow execution and approvals
- **PostgreSQL** - Workflows, results, approval queue, artifacts
- **Pydantic** - Configuration validation and type safety

**LLM Orchestration:**
- **LangGraph** - Simple synchronous workflow execution
- **LiteLLM** - Universal provider abstraction (OpenRouter, Anthropic, OpenAI, etc.)
- **Langfuse** - Observability and experiment tracking

**Optional Integrations:**
- **Verbalized Sampling** - Python library for diversity improvement
- **TruLens** - Pre-built evaluators
- **Weave** - Alternative observability platform

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface (CLI/API)                  │
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
│  - LangGraph workflow execution                              │
│  - Result persistence                                        │
└─────────┬─────────────────┴─────────────────┬───────────────┘
          │                                   │
┌─────────▼──────────────┐       ┌───────────▼──────────────┐
│  Generation Strategies │       │   Quality Evaluator      │
│  - Standard            │       │   - Rubric-based         │
│  - Verbalized Sampling │       │   - Pairwise A/B         │
│  - Chain of Thought    │       │   - Judge ensembles      │
│  - Few-Shot            │       │   - Custom evaluators    │
└─────────┬──────────────┘       └───────────┬──────────────┘
          │                                   │
┌─────────▼───────────────────────────────────▼───────────────┐
│                      LLM Provider Gateway                    │
│                        (LiteLLM)                             │
│  - OpenRouter, Anthropic, OpenAI, DeepSeek, etc.            │
└──────────────────────────────────────────────────────────────┘
```

### Database Schema

```sql
-- Workflow executions
CREATE TABLE workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID REFERENCES experiments(id),
    type VARCHAR(100) NOT NULL,           -- 'generate_draft', 'apply_feedback'
    status VARCHAR(20) NOT NULL,          -- 'running', 'completed', 'failed'
    config JSONB NOT NULL,                -- Workflow configuration
    input_data JSONB NOT NULL,
    output_data JSONB,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Approval queue (HITL between workflows)
CREATE TABLE approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID REFERENCES workflows(id),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- 'pending', 'approved', 'rejected'
    artifact_type VARCHAR(50) NOT NULL,             -- 'scene_draft', 'code_review'
    artifact_data JSONB NOT NULL,                   -- What to review
    feedback TEXT,                                  -- Human input
    next_workflow_type VARCHAR(100),                -- Workflow to trigger after approval
    next_workflow_input JSONB,
    reviewed_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    reviewed_at TIMESTAMP
);

-- Experiments (Taguchi DOE)
CREATE TABLE experiments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    workflow_type VARCHAR(100) NOT NULL,
    design_type VARCHAR(20) NOT NULL,     -- 'taguchi_l8', 'taguchi_l16', etc.
    variables JSONB NOT NULL,             -- Variable definitions
    test_configs JSONB NOT NULL,          -- Generated test configurations
    status VARCHAR(20) NOT NULL,          -- 'running', 'completed', 'failed'
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Quality evaluations
CREATE TABLE quality_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID REFERENCES workflows(id),
    evaluator_name VARCHAR(100) NOT NULL,
    dimensions JSONB NOT NULL,            -- {"clarity": 0.85, "depth": 0.75}
    overall_score DECIMAL(5,4) NOT NULL,
    cost_usd DECIMAL(10,6) NOT NULL,
    latency_ms INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Run ledger (reproducibility)
CREATE TABLE run_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID REFERENCES experiments(id),
    test_number INTEGER NOT NULL,
    config_snapshot JSONB NOT NULL,       -- Exact config used
    provider VARCHAR(50) NOT NULL,
    model VARCHAR(100) NOT NULL,
    generation_strategy VARCHAR(50) NOT NULL,
    seed INTEGER,
    git_commit VARCHAR(40),               -- Code version
    framework_version VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Core Components

### 1. BaseWorkflowService

**Purpose:** Abstract base class for all workflow implementations.

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, Dict, Any
from pydantic import BaseModel
from langgraph.graph import StateGraph
from generation_strategies import get_strategy

TInput = TypeVar('TInput', bound=BaseModel)
TOutput = TypeVar('TOutput', bound=BaseModel)

class BaseWorkflowService(Generic[TInput, TOutput], ABC):
    """
    Base class for all LLM workflow implementations.

    Key responsibilities:
    - Load workflow configuration from YAML
    - Select generation strategy based on config
    - Execute workflow using LangGraph
    - Return type-safe output
    """

    def __init__(
        self,
        workflow_config: Optional[WorkflowConfig] = None,
        api_key: Optional[str] = None
    ):
        self.config = workflow_config or self._load_default_config()
        self.api_key = api_key or self._resolve_api_key()
        self.model = self._initialize_model()
        self.graph = self._build_workflow()

    @abstractmethod
    def _build_workflow(self) -> StateGraph:
        """
        Define workflow logic using LangGraph.

        Subclasses implement domain-specific workflow steps.
        """
        pass

    async def execute(self, input_data: TInput) -> TOutput:
        """
        Execute workflow with given input.

        Returns:
            Type-safe output matching TOutput schema
        """
        # Select generation strategy from config
        strategy_name = self.config.generation_strategy
        strategy = get_strategy(strategy_name)

        # Execute workflow graph
        result = await self.graph.ainvoke({
            "input": input_data.dict(),
            "config": self.config.dict(),
            "strategy": strategy
        })

        # Validate and return
        return self._validate_output(result)

    @abstractmethod
    def _validate_output(self, result: Dict[str, Any]) -> TOutput:
        """Validate and convert result to TOutput schema."""
        pass

    def _load_default_config(self) -> WorkflowConfig:
        """Load default configuration from YAML."""
        config_path = f"workflows/defaults/{self.__class__.__name__.lower()}.yaml"
        return WorkflowConfig.from_yaml(config_path)

    def _initialize_model(self) -> LLMModel:
        """Initialize LLM via LiteLLM (provider-agnostic)."""
        from litellm import completion

        return LiteLLMWrapper(
            model=self.config.model,
            temperature=self.config.temperature,
            api_key=self.api_key
        )
```

**Example Workflow Implementation:**

```python
from pydantic import BaseModel
from langgraph.graph import StateGraph

class CodeReviewInput(BaseModel):
    code: str
    language: str
    context: Optional[str] = None

class CodeReviewOutput(BaseModel):
    issues: List[Dict[str, str]]
    suggestions: List[str]
    quality_score: float

class CodeReviewWorkflow(BaseWorkflowService[CodeReviewInput, CodeReviewOutput]):
    """Code review workflow with configurable generation strategy."""

    def _build_workflow(self) -> StateGraph:
        graph = StateGraph()

        # Define workflow steps
        graph.add_node("analyze", self._analyze_code)
        graph.add_node("suggest", self._generate_suggestions)
        graph.add_node("score", self._compute_quality_score)

        # Define edges
        graph.add_edge("analyze", "suggest")
        graph.add_edge("suggest", "score")
        graph.set_entry_point("analyze")
        graph.set_finish_point("score")

        return graph.compile()

    async def _analyze_code(self, state: dict) -> dict:
        """Analyze code for issues using configured generation strategy."""
        strategy = state["strategy"]

        prompt = self.config.render_prompt("analyze", {
            "code": state["input"]["code"],
            "language": state["input"]["language"]
        })

        # Strategy decides HOW to generate (standard, VS, CoT, etc.)
        analysis = await strategy.generate(
            prompt=prompt,
            model=self.model,
            config=self.config.dict()
        )

        state["analysis"] = analysis
        return state

    async def _generate_suggestions(self, state: dict) -> dict:
        """Generate improvement suggestions."""
        # Similar pattern with strategy
        ...

    async def _compute_quality_score(self, state: dict) -> dict:
        """Compute overall quality score."""
        # Scoring logic
        ...

    def _validate_output(self, result: dict) -> CodeReviewOutput:
        return CodeReviewOutput(**result)
```

### 2. Generation Strategies Registry

**Purpose:** Pluggable strategies for text generation (standard, VS, CoT, few-shot, etc.).

```python
# generation_strategies.py

from typing import Protocol, Dict, Any
from abc import abstractmethod

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

class StandardStrategy:
    """Standard prompting - direct LLM call."""

    async def generate(self, prompt: str, model: LLMModel, config: Dict[str, Any]) -> str:
        response = await model.ainvoke(prompt)
        return response.content

class VerbalizedSamplingStrategy:
    """
    Verbalized Sampling strategy (optional).

    Requires: pip install verbalized-sampling
    """

    async def generate(self, prompt: str, model: LLMModel, config: Dict[str, Any]) -> str:
        try:
            from verbalized_sampling import verbalize
        except ImportError:
            raise ImportError(
                "Verbalized Sampling requires: pip install verbalized-sampling"
            )

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

    async def generate(self, prompt: str, model: LLMModel, config: Dict[str, Any]) -> str:
        cot_prompt = f"{prompt}\n\nLet's think step by step:"
        response = await model.ainvoke(cot_prompt)
        return response.content

class FewShotStrategy:
    """Few-shot prompting with examples."""

    async def generate(self, prompt: str, model: LLMModel, config: Dict[str, Any]) -> str:
        examples = config.get("few_shot_examples", [])
        few_shot_prompt = self._build_few_shot(prompt, examples)
        response = await model.ainvoke(few_shot_prompt)
        return response.content

    def _build_few_shot(self, prompt: str, examples: List[Dict]) -> str:
        formatted = "\n\n".join([
            f"Example {i+1}:\nInput: {ex['input']}\nOutput: {ex['output']}"
            for i, ex in enumerate(examples)
        ])
        return f"{formatted}\n\nNow:\nInput: {prompt}\nOutput:"

# Strategy registry
GENERATION_STRATEGIES: Dict[str, GenerationStrategy] = {
    "standard": StandardStrategy(),
    "chain_of_thought": ChainOfThoughtStrategy(),
    "few_shot": FewShotStrategy(),
}

# Optional strategies (loaded if available)
try:
    GENERATION_STRATEGIES["verbalized_sampling"] = VerbalizedSamplingStrategy()
except ImportError:
    pass

def get_strategy(name: str) -> GenerationStrategy:
    """Get strategy by name."""
    if name not in GENERATION_STRATEGIES:
        available = ", ".join(GENERATION_STRATEGIES.keys())
        raise ValueError(
            f"Unknown strategy: {name}. Available: {available}"
        )
    return GENERATION_STRATEGIES[name]

def register_strategy(name: str, strategy: GenerationStrategy):
    """Register custom strategy."""
    GENERATION_STRATEGIES[name] = strategy
```

**User can add custom strategies:**

```python
# user_code.py
from llm_optimizer import register_strategy

class MyCustomStrategy:
    async def generate(self, prompt, model, config):
        # Custom logic (e.g., retrieval-augmented generation)
        context = await self._retrieve_context(prompt)
        augmented_prompt = f"Context: {context}\n\n{prompt}"
        response = await model.ainvoke(augmented_prompt)
        return response.content

register_strategy("rag", MyCustomStrategy())

# Now can use in experiments:
# generation_strategy: {1: "standard", 2: "rag"}
```

### 3. Taguchi Experiment Framework

**Purpose:** Efficiently test multiple variables using orthogonal arrays.

```python
# taguchi.py

from typing import Dict, List, Any
from itertools import product
import numpy as np
from pydantic import BaseModel

class ExperimentVariable(BaseModel):
    """Definition of a variable to test."""
    name: str
    level_1: Any
    level_2: Any

class TaguchiExperiment:
    """
    Taguchi Design of Experiments framework.

    Supports L8, L16, L18 orthogonal arrays.
    """

    # L8 orthogonal array (7 variables, 2 levels, 8 experiments)
    L8_ARRAY = np.array([
        [1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 2, 2, 2, 2],
        [1, 2, 2, 1, 1, 2, 2],
        [1, 2, 2, 2, 2, 1, 1],
        [2, 1, 2, 1, 2, 1, 2],
        [2, 1, 2, 2, 1, 2, 1],
        [2, 2, 1, 1, 2, 2, 1],
        [2, 2, 1, 2, 1, 1, 2],
    ])

    # L16 orthogonal array (15 variables, 2 levels, 16 experiments)
    L16_ARRAY = np.array([
        # ... (standard L16 array definition)
    ])

    def __init__(
        self,
        variables: Dict[str, ExperimentVariable],
        design_type: str = "taguchi_l8"
    ):
        self.variables = variables
        self.design_type = design_type
        self.array = self._get_array()
        self.test_configs = self._generate_configs()

    def _get_array(self) -> np.ndarray:
        """Get orthogonal array for design type."""
        if self.design_type == "taguchi_l8":
            return self.L8_ARRAY
        elif self.design_type == "taguchi_l16":
            return self.L16_ARRAY
        else:
            raise ValueError(f"Unsupported design: {self.design_type}")

    def _generate_configs(self) -> List[Dict[str, Any]]:
        """
        Generate test configurations from orthogonal array.

        Returns:
            List of configs, one per test
        """
        configs = []
        var_names = list(self.variables.keys())

        for test_row in self.array:
            config = {}
            for i, var_name in enumerate(var_names[:len(test_row)]):
                var = self.variables[var_name]
                level = test_row[i]
                config[var_name] = var.level_1 if level == 1 else var.level_2
            configs.append(config)

        return configs

    def analyze_main_effects(
        self,
        results: List[float]
    ) -> Dict[str, Dict[str, float]]:
        """
        Compute main effects for each variable.

        Args:
            results: Utility scores for each test

        Returns:
            Main effects analysis
        """
        main_effects = {}
        var_names = list(self.variables.keys())

        for i, var_name in enumerate(var_names[:self.array.shape[1]]):
            # Average utility for level 1
            level_1_tests = self.array[:, i] == 1
            avg_level_1 = np.mean([results[j] for j in range(len(results)) if level_1_tests[j]])

            # Average utility for level 2
            level_2_tests = self.array[:, i] == 2
            avg_level_2 = np.mean([results[j] for j in range(len(results)) if level_2_tests[j]])

            main_effects[var_name] = {
                "level_1_avg": avg_level_1,
                "level_2_avg": avg_level_2,
                "effect_size": avg_level_2 - avg_level_1,
                "contribution_pct": self._compute_contribution(var_name, results)
            }

        return main_effects

    def _compute_contribution(self, var_name: str, results: List[float]) -> float:
        """Compute percentage contribution of variable to total variance."""
        # Sum of squares calculation
        # (Simplified - full Taguchi uses ANOVA)
        ...

    def identify_optimal_config(
        self,
        main_effects: Dict[str, Dict[str, float]]
    ) -> Dict[str, Any]:
        """
        Identify optimal configuration from main effects.

        Selects level with higher average utility for each variable.
        """
        optimal = {}
        for var_name, effects in main_effects.items():
            if effects["level_1_avg"] > effects["level_2_avg"]:
                optimal[var_name] = self.variables[var_name].level_1
            else:
                optimal[var_name] = self.variables[var_name].level_2

        return optimal
```

**Example Usage:**

```python
# Define experiment
variables = {
    "temperature": ExperimentVariable(name="temperature", level_1=0.3, level_2=0.7),
    "model": ExperimentVariable(name="model", level_1="deepseek/deepseek-coder-v2", level_2="anthropic/claude-3.5-sonnet"),
    "context_size": ExperimentVariable(name="context_size", level_1="file_only", level_2="full_module"),
    "generation_strategy": ExperimentVariable(name="generation_strategy", level_1="standard", level_2="verbalized_sampling"),
}

experiment = TaguchiExperiment(variables, design_type="taguchi_l8")

# Run 8 tests
results = []
for i, config in enumerate(experiment.test_configs):
    workflow = CodeReviewWorkflow(workflow_config=config)
    output = await workflow.execute(test_input)
    score = await evaluator.evaluate(output)
    results.append(score.utility)

# Analyze main effects
main_effects = experiment.analyze_main_effects(results)

# Output:
# {
#   "temperature": {"level_1_avg": 0.65, "level_2_avg": 0.72, "effect_size": 0.07, "contribution_pct": 15},
#   "model": {"level_1_avg": 0.68, "level_2_avg": 0.75, "effect_size": 0.07, "contribution_pct": 15},
#   "context_size": {"level_1_avg": 0.60, "level_2_avg": 0.85, "effect_size": 0.25, "contribution_pct": 55},
#   "generation_strategy": {"level_1_avg": 0.70, "level_2_avg": 0.78, "effect_size": 0.08, "contribution_pct": 15}
# }

# Identify optimal config
optimal = experiment.identify_optimal_config(main_effects)
# {"temperature": 0.7, "model": "anthropic/claude-3.5-sonnet", "context_size": "full_module", "generation_strategy": "verbalized_sampling"}
```

### 4. Quality Evaluation Framework

**Purpose:** Evaluate workflow outputs across multiple dimensions.

```python
# evaluators.py

from typing import Generic, TypeVar, List, Dict, Optional
from pydantic import BaseModel
from abc import ABC, abstractmethod

T = TypeVar('T', bound=BaseModel)

class QualityScore(BaseModel):
    """Quality evaluation result."""
    dimensions: Dict[str, float]      # {"clarity": 0.85, "depth": 0.75}
    overall_score: float              # Aggregate score
    cost_usd: float
    latency_ms: int
    utility: float                    # Combined metric

class Evaluator(Generic[T], ABC):
    """Base class for quality evaluators."""

    @abstractmethod
    async def evaluate(self, output: T, context: Optional[Dict] = None) -> QualityScore:
        """Evaluate workflow output."""
        pass

class RubricEvaluator(Evaluator[T]):
    """
    Rubric-based evaluation using LLM-as-judge.

    Evaluates output across multiple dimensions with detailed rubrics.
    """

    def __init__(
        self,
        rubric_path: str,
        judge_model: str = "anthropic/claude-3.5-sonnet",
        api_key: Optional[str] = None
    ):
        self.rubric = self._load_rubric(rubric_path)
        self.judge_model = judge_model
        self.api_key = api_key
        self.model = self._initialize_model()

    async def evaluate(self, output: T, context: Optional[Dict] = None) -> QualityScore:
        """
        Evaluate output using rubric dimensions.

        Returns:
            QualityScore with dimension scores and overall score
        """
        dimension_scores = {}

        # Evaluate each dimension
        for dimension, rubric_text in self.rubric["dimensions"].items():
            prompt = self._build_eval_prompt(dimension, rubric_text, output, context)

            response = await self.model.ainvoke(prompt)
            score = self._extract_score(response.content)
            dimension_scores[dimension] = score

        # Compute overall score
        weights = self.rubric.get("weights", {})
        overall_score = self._compute_weighted_average(dimension_scores, weights)

        return QualityScore(
            dimensions=dimension_scores,
            overall_score=overall_score,
            cost_usd=response.usage.cost,
            latency_ms=response.latency_ms,
            utility=overall_score  # Will be updated with cost/time penalties
        )

    def _build_eval_prompt(
        self,
        dimension: str,
        rubric: str,
        output: T,
        context: Optional[Dict]
    ) -> str:
        """Build evaluation prompt for dimension."""
        return f"""
You are evaluating the quality of an output on the dimension: {dimension}

Rubric:
{rubric}

Output to evaluate:
{output.json(indent=2)}

Context:
{context or "None"}

Provide a score from 0.0 to 1.0 and explain your reasoning.

Format:
Score: <number>
Reasoning: <explanation>
"""

    def _extract_score(self, response: str) -> float:
        """Extract numeric score from LLM response."""
        # Parse "Score: 0.85" from response
        import re
        match = re.search(r"Score:\s*([0-9.]+)", response)
        if match:
            return float(match.group(1))
        raise ValueError(f"Could not extract score from: {response}")

class PairwiseEvaluator(Evaluator[T]):
    """
    Pairwise A/B comparison evaluator.

    Compares two outputs and determines which is better.
    More reliable than absolute scoring for some tasks.
    """

    async def compare(
        self,
        output_a: T,
        output_b: T,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Compare two outputs.

        Returns:
            {"winner": "A" | "B" | "tie", "reasoning": str, "confidence": float}
        """
        # Randomize order to avoid position bias
        import random
        order = random.choice(["AB", "BA"])

        if order == "AB":
            first, second = output_a, output_b
        else:
            first, second = output_b, output_a

        prompt = f"""
Compare these two outputs and determine which is better.

Output 1:
{first.json(indent=2)}

Output 2:
{second.json(indent=2)}

Context:
{context or "None"}

Which output is better? Provide:
1. Winner: 1 | 2 | tie
2. Reasoning: Detailed explanation
3. Confidence: 0.0 to 1.0
"""

        response = await self.model.ainvoke(prompt)
        result = self._parse_comparison(response.content)

        # Map back to A/B after debiasing
        if order == "BA":
            result["winner"] = "B" if result["winner"] == "1" else ("A" if result["winner"] == "2" else "tie")
        else:
            result["winner"] = "A" if result["winner"] == "1" else ("B" if result["winner"] == "2" else "tie")

        return result

class EnsembleEvaluator(Evaluator[T]):
    """
    Ensemble of multiple evaluators.

    Combines judgments from multiple LLM judges to reduce bias.
    """

    def __init__(
        self,
        judge_models: List[str],
        rubric_path: str,
        api_key: Optional[str] = None
    ):
        self.evaluators = [
            RubricEvaluator(rubric_path, model, api_key)
            for model in judge_models
        ]

    async def evaluate(self, output: T, context: Optional[Dict] = None) -> QualityScore:
        """
        Evaluate using ensemble of judges.

        Returns:
            Aggregated quality score (median of judges)
        """
        import asyncio

        # Run all evaluators in parallel
        scores = await asyncio.gather(*[
            evaluator.evaluate(output, context)
            for evaluator in self.evaluators
        ])

        # Aggregate dimension scores (median)
        aggregated_dimensions = {}
        for dimension in scores[0].dimensions.keys():
            values = [score.dimensions[dimension] for score in scores]
            aggregated_dimensions[dimension] = np.median(values)

        # Aggregate overall score
        overall_scores = [score.overall_score for score in scores]
        aggregated_overall = np.median(overall_scores)

        # Sum costs
        total_cost = sum(score.cost_usd for score in scores)
        max_latency = max(score.latency_ms for score in scores)

        return QualityScore(
            dimensions=aggregated_dimensions,
            overall_score=aggregated_overall,
            cost_usd=total_cost,
            latency_ms=max_latency,
            utility=aggregated_overall
        )
```

**Example Rubric (YAML):**

```yaml
# rubrics/code_review.yaml
dimensions:
  correctness:
    description: "Are identified issues actually problems?"
    scale:
      - 0.0-0.3: "Many false positives or missed critical issues"
      - 0.4-0.6: "Some false positives, catches most issues"
      - 0.7-0.9: "Accurate issue identification"
      - 1.0: "Perfect accuracy, no false positives"

  actionability:
    description: "Are suggestions specific and implementable?"
    scale:
      - 0.0-0.3: "Vague or generic advice"
      - 0.4-0.6: "Some specific suggestions"
      - 0.7-0.9: "Clear, actionable recommendations"
      - 1.0: "Detailed, step-by-step guidance"

  depth:
    description: "Does review go beyond surface-level observations?"
    scale:
      - 0.0-0.3: "Only basic syntax issues"
      - 0.4-0.6: "Some logic/design feedback"
      - 0.7-0.9: "Architectural and performance insights"
      - 1.0: "Deep analysis of design patterns and trade-offs"

weights:
  correctness: 0.5
  actionability: 0.3
  depth: 0.2
```

### 5. Multi-Objective Optimization

**Purpose:** Balance quality, cost, and time trade-offs.

```python
# optimization.py

from typing import List, Tuple
import numpy as np
from dataclasses import dataclass

@dataclass
class TestResult:
    """Result from single test."""
    config: Dict[str, Any]
    quality_score: float
    cost_usd: float
    latency_ms: int

class MultiObjectiveOptimizer:
    """
    Multi-objective optimization for LLM workflows.

    Computes:
    - Utility function (weighted combination)
    - Pareto frontier (non-dominated solutions)
    """

    def __init__(
        self,
        w_quality: float = 0.7,
        w_cost: float = 0.2,
        w_time: float = 0.1
    ):
        self.w_quality = w_quality
        self.w_cost = w_cost
        self.w_time = w_time

    def compute_utility(self, results: List[TestResult]) -> List[float]:
        """
        Compute utility scores for all results.

        Utility = w_q * quality - w_c * normalized_cost - w_t * normalized_time

        Returns:
            List of utility scores
        """
        # Normalize cost and time to [0, 1]
        costs = np.array([r.cost_usd for r in results])
        times = np.array([r.latency_ms for r in results])

        normalized_costs = (costs - costs.min()) / (costs.max() - costs.min() + 1e-9)
        normalized_times = (times - times.min()) / (times.max() - times.min() + 1e-9)

        utilities = []
        for i, result in enumerate(results):
            utility = (
                self.w_quality * result.quality_score
                - self.w_cost * normalized_costs[i]
                - self.w_time * normalized_times[i]
            )
            utilities.append(utility)

        return utilities

    def compute_pareto_frontier(
        self,
        results: List[TestResult]
    ) -> List[int]:
        """
        Compute Pareto frontier (Quality vs Cost).

        A solution is Pareto-optimal if no other solution is better
        in both quality AND cost.

        Returns:
            Indices of Pareto-optimal solutions
        """
        pareto_indices = []

        for i, result_i in enumerate(results):
            is_dominated = False

            for j, result_j in enumerate(results):
                if i == j:
                    continue

                # Check if j dominates i
                # (j has higher quality AND lower cost)
                if (result_j.quality_score >= result_i.quality_score and
                    result_j.cost_usd <= result_i.cost_usd and
                    (result_j.quality_score > result_i.quality_score or
                     result_j.cost_usd < result_i.cost_usd)):
                    is_dominated = True
                    break

            if not is_dominated:
                pareto_indices.append(i)

        return pareto_indices

    def plot_pareto(
        self,
        results: List[TestResult],
        pareto_indices: List[int],
        output_path: str = "pareto.svg"
    ):
        """
        Visualize Pareto frontier.

        - X-axis: Cost (USD)
        - Y-axis: Quality Score
        - Bubble size: Latency (ms)
        - Pareto-optimal solutions highlighted
        """
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(10, 6))

        # Plot all results
        qualities = [r.quality_score for r in results]
        costs = [r.cost_usd for r in results]
        times = [r.latency_ms for r in results]

        ax.scatter(
            costs,
            qualities,
            s=[t/10 for t in times],  # Bubble size proportional to time
            alpha=0.6,
            label="All configurations"
        )

        # Highlight Pareto frontier
        pareto_costs = [costs[i] for i in pareto_indices]
        pareto_qualities = [qualities[i] for i in pareto_indices]
        pareto_times = [times[i] for i in pareto_indices]

        ax.scatter(
            pareto_costs,
            pareto_qualities,
            s=[t/10 for t in pareto_times],
            color='red',
            marker='*',
            s=200,
            label="Pareto optimal",
            zorder=10
        )

        # Connect Pareto points
        sorted_pareto = sorted(zip(pareto_costs, pareto_qualities))
        ax.plot(
            [p[0] for p in sorted_pareto],
            [p[1] for p in sorted_pareto],
            'r--',
            alpha=0.5
        )

        ax.set_xlabel("Cost (USD)")
        ax.set_ylabel("Quality Score")
        ax.set_title("Pareto Frontier: Quality vs Cost")
        ax.legend()
        ax.grid(alpha=0.3)

        plt.savefig(output_path)
        print(f"Pareto frontier saved to {output_path}")
```

---

## Configuration Specifications

### Workflow Configuration (YAML)

```yaml
# workflows/defaults/code_review.yaml
name: "code_review"
version: "1.0"
description: "Code review workflow with configurable generation strategy"

# Model configuration
models:
  analyzer:
    model: "deepseek/deepseek-coder-v2"
    temperature: 0.3
    max_tokens: 2000

    # Generation strategy (experimental variable)
    generation_strategy: "standard"

    # Strategy-specific parameters (only used if strategy enabled)
    vs_k: 5
    vs_tau: 0.10
    few_shot_examples: []

# Provider configuration
provider:
  type: "openrouter"      # or "anthropic", "openai", "litellm"
  api_key_env: "OPENROUTER_API_KEY"
  fallback_providers: ["anthropic"]

# Prompt templates
prompts:
  analyze: "code_review/analyze.jinja2"
  suggest: "code_review/suggest.jinja2"

# Quality evaluation
evaluation:
  rubric: "rubrics/code_review.yaml"
  judge_model: "anthropic/claude-3.5-sonnet"
  ensemble:
    enabled: false
    judges: ["anthropic/claude-3.5-sonnet", "openai/gpt-4o"]

# Observability
observability:
  langfuse:
    enabled: true
    project: "llm-optimizer"
  trace_inputs: true
  trace_outputs: true
```

### Experiment Configuration (YAML)

```yaml
# experiments/code_review_optimization.yaml
name: "code_review_optimization"
workflow: "code_review"
description: "Optimize code review workflow for quality and cost"

# Experiment design
method:
  type: "taguchi_l8"      # or "taguchi_l16", "full_factorial"

# Variables to test (2 levels each)
variables:
  # Variable 1: Temperature
  temperature:
    1: 0.3    # Conservative
    2: 0.7    # Creative

  # Variable 2: Model
  model:
    1: "deepseek/deepseek-coder-v2"
    2: "anthropic/claude-3.5-sonnet"

  # Variable 3: Context size
  context_size:
    1: "file_only"
    2: "full_module"

  # Variable 4: Generation strategy ⭐
  generation_strategy:
    1: "standard"
    2: "verbalized_sampling"

# Multi-objective optimization weights
utility_weights:
  quality: 0.6
  cost: 0.3
  time: 0.1

# Test data
test_cases:
  - input_file: "test_data/react_component.js"
  - input_file: "test_data/python_service.py"
  - input_file: "test_data/sql_query.sql"

# Output
output:
  results_dir: "results/code_review_optimization"
  save_pareto_plot: true
  export_to_langfuse: true
```

### Approval Queue API

**Create Approval:**
```http
POST /api/approvals
Content-Type: application/json

{
  "workflow_id": "uuid",
  "artifact_type": "scene_draft",
  "artifact_data": {
    "scene_number": 42,
    "content": "The detective entered the room...",
    "quality_scores": {...}
  },
  "next_workflow_type": "apply_feedback"
}

Response 201:
{
  "approval_id": "uuid",
  "status": "pending",
  "created_at": "2025-10-25T10:00:00Z"
}
```

**List Pending Approvals:**
```http
GET /api/approvals?status=pending

Response 200:
{
  "approvals": [
    {
      "id": "uuid",
      "artifact_type": "scene_draft",
      "artifact_data": {...},
      "created_at": "2025-10-25T10:00:00Z"
    }
  ]
}
```

**Submit Approval:**
```http
POST /api/approvals/{id}/approve
Content-Type: application/json

{
  "feedback": "Great scene! Add more sensory details about the room.",
  "next_workflow_input": {
    "scene_id": 42,
    "feedback_text": "Add sensory details"
  }
}

Response 200:
{
  "approval_id": "uuid",
  "status": "approved",
  "next_workflow_id": "uuid",  # Triggered workflow
  "reviewed_at": "2025-10-25T10:05:00Z"
}
```

---

## MVP Features (Phase 1)

### Must-Have Features

1. **Core Workflow System**
   - BaseWorkflowService with type-safe generics
   - LangGraph integration for simple workflows
   - YAML configuration loading
   - Generation strategies registry

2. **Taguchi Experiments**
   - L8 orthogonal array support
   - Variable definitions (2 levels)
   - Test configuration generation
   - Main effects analysis

3. **Quality Evaluation**
   - Rubric-based evaluator (LLM-as-judge)
   - Multi-dimensional scoring
   - Cost and latency tracking

4. **Multi-Objective Optimization**
   - Utility function (quality - cost - time)
   - Pareto frontier computation
   - Pareto visualization (Quality vs Cost)

5. **Provider Abstraction**
   - LiteLLM integration
   - OpenRouter support
   - API key management

6. **Observability**
   - Langfuse integration (export results)
   - Run ledger (reproducibility)
   - Basic logging

### Nice-to-Have (Phase 1)

1. **Generation Strategies**
   - Standard prompting ✅
   - Chain-of-thought ✅
   - Verbalized Sampling (optional) ⚠️

2. **Approval Queue**
   - Database schema ✅
   - REST API endpoints ✅
   - Simple UI (later)

---

## Post-MVP Features (Phase 2)

### Advanced Evaluation

1. **Pairwise A/B Evaluation**
   - Order randomization (debias position bias)
   - Confidence scoring
   - Win-rate tracking

2. **Judge Ensembles**
   - Multiple LLM judges
   - Median aggregation
   - Inter-rater reliability

3. **Custom Evaluators**
   - User-defined Python evaluators
   - Integration with TruLens evaluators
   - Programmatic validators (unit tests, linters)

### Advanced DOE

1. **L16 and L18 Arrays**
   - More variables (up to 15)
   - Higher-order interactions

2. **Confirmation Experiments**
   - Validate optimal config with fresh tests
   - Statistical significance testing

### Advanced Workflows

1. **Multi-Stage Workflows**
   - Draft → Review → Revise → Polish
   - Approval gates between stages

2. **Parallel Generation**
   - Generate N drafts in parallel
   - Best-of-N selection
   - Merge strategies

### Platform Features

1. **Web UI**
   - Approval queue dashboard
   - Experiment monitoring
   - Pareto frontier visualization (interactive)

2. **CLI Tool**
   - `llm-optimizer experiment run <config.yaml>`
   - `llm-optimizer analyze <results.json>`
   - `llm-optimizer approvals list`

3. **Integration Plugins**
   - Weave export (alternative to Langfuse)
   - TruLens evaluator wrappers
   - Custom observability backends

---

## Implementation Roadmap

### Week 1-2: Core Framework

**Goals:**
- BaseWorkflowService implementation
- Generation strategies registry
- YAML configuration parsing
- LiteLLM integration

**Deliverables:**
- `base_workflow.py` - Abstract base class
- `generation_strategies.py` - Strategy registry
- `config.py` - YAML loading and validation
- `providers.py` - LiteLLM wrapper

**Tests:**
- Unit tests for strategy selection
- Integration test with OpenRouter
- Configuration validation tests

### Week 3-4: Taguchi Experiments

**Goals:**
- L8 orthogonal array implementation
- Variable definition and mapping
- Test configuration generation
- Main effects analysis

**Deliverables:**
- `taguchi.py` - Experiment framework
- `analysis.py` - Main effects computation
- Example experiment YAML

**Tests:**
- L8 array generation tests
- Main effects calculation tests
- End-to-end experiment test

### Week 5-6: Quality Evaluation

**Goals:**
- Rubric-based evaluator
- LLM-as-judge implementation
- Cost and latency tracking
- Utility function

**Deliverables:**
- `evaluators.py` - Evaluator classes
- `optimization.py` - Utility and Pareto
- Example rubric YAML

**Tests:**
- Evaluator accuracy tests
- Utility function tests
- Pareto frontier tests

### Week 7-8: Multi-Objective Optimization

**Goals:**
- Pareto frontier computation
- Visualization (matplotlib)
- Optimal config identification

**Deliverables:**
- `optimization.py` - Pareto methods
- Pareto plot generation
- Analysis report generation

**Tests:**
- Pareto computation tests
- Plot generation tests

### Week 9-10: Observability

**Goals:**
- Langfuse integration
- Run ledger implementation
- Experiment result export

**Deliverables:**
- `observability.py` - Langfuse wrapper
- Database migrations for run ledger
- Export utilities

**Tests:**
- Langfuse export tests
- Run ledger tests

### Week 11-12: Documentation & Examples

**Goals:**
- User guide
- API documentation
- Example workflows (code review, scene drafting)
- Tutorial notebooks

**Deliverables:**
- `README.md` with quick start
- `docs/` directory with guides
- `examples/` directory with workflows
- Jupyter notebooks

---

## Competitive Positioning

### vs DSPy

**DSPy:** Auto-optimizes prompts using their framework
- Must use DSPy pipeline structure
- Automated but opaque
- Hard to control optimization strategy

**Us:** User tests strategies explicitly
- Works with any LangGraph workflow
- Transparent A/B testing with Taguchi
- Clear which variable contributes what (main effects)

**Our Advantage:**
- ✅ More control over optimization
- ✅ Works with existing workflows
- ✅ Taguchi efficiency (8 tests vs 16 for DSPy grid search)

### vs LangSmith

**LangSmith:** Observability and manual A/B testing
- Run config A, run config B, compare
- No systematic experiment design
- Manual analysis

**Us:** Automated DOE + Observability
- 8 experiments test 4 variables (Taguchi)
- Main effects analysis automatic
- Integrates with LangSmith for observability

**Our Advantage:**
- ✅ Systematic experiment design
- ✅ Efficient testing (fewer experiments)
- ✅ Automatic optimal config identification

### vs Minitab (Traditional DOE)

**Minitab:** Taguchi for manufacturing
- Not LLM-aware
- No quality evaluation
- Manual data entry

**Us:** Taguchi for LLMs
- Built-in LLM-as-judge evaluation
- Cost and latency tracking
- API integration

**Our Advantage:**
- ✅ LLM-specific metrics (quality, cost, latency)
- ✅ Automated evaluation
- ✅ Modern API/CLI interface

---

## Success Metrics

### Technical Metrics

1. **Experiment Efficiency**
   - Target: 8 experiments (L8) vs 16 (full factorial) = 50% reduction
   - Measure: Experiments required to find optimal config

2. **Quality Improvement**
   - Target: 10-30% quality improvement via optimization
   - Measure: Quality score before vs after optimization

3. **Cost Reduction**
   - Target: 20-50% cost reduction without quality loss
   - Measure: Identify cost-effective configs on Pareto frontier

4. **Time to Optimize**
   - Target: < 2 hours to run full L8 experiment
   - Measure: Wall-clock time for complete experiment

### User Metrics

1. **Adoption**
   - Target: 3 distinct workflows implemented (code review, scene drafting, docs)
   - Measure: Number of BaseWorkflowService subclasses

2. **Experiment Runs**
   - Target: 10+ experiments run in first month
   - Measure: Experiments logged in database

3. **User Feedback**
   - Target: "This helped me find optimal config I wouldn't have guessed"
   - Measure: Qualitative feedback

---

## Risks and Mitigations

### Risk 1: LLM-as-Judge Unreliability

**Risk:** Evaluator scores may be inconsistent or biased.

**Mitigation:**
- Implement pairwise A/B (more reliable than absolute scoring)
- Support judge ensembles (median of multiple judges)
- Allow programmatic evaluators (unit tests, metrics)
- Document evaluator limitations

### Risk 2: Verbalized Sampling Overhead

**Risk:** VS adds latency and cost (k API calls per generation).

**Mitigation:**
- Make VS optional (just another strategy)
- Test VS as experimental variable (measure if benefit > cost)
- Document when VS is worth using (creative tasks, large models)

### Risk 3: Taguchi Assumes No Interactions

**Risk:** Taguchi orthogonal arrays assume variables don't interact strongly.

**Mitigation:**
- Document assumption clearly
- Recommend confirmation experiments for critical workflows
- Support full factorial for small variable counts (if interactions suspected)

### Risk 4: Provider Rate Limits

**Risk:** Running 8-16 experiments may hit API rate limits.

**Mitigation:**
- Implement retry with exponential backoff
- Support provider rotation (OpenRouter → Anthropic fallback)
- Batch experiments with delays
- Document rate limit considerations

---

## Open Questions

1. **How to handle 3+ level variables?**
   - Taguchi supports 3-level arrays (L9, L27)
   - Should we support in MVP or defer?
   - **Decision:** Defer to post-MVP (2-level is 80% of use cases)

2. **Should we support LangChain (not just LangGraph)?**
   - LangChain has larger user base
   - LangGraph is newer but more powerful
   - **Decision:** LangGraph for MVP (simpler), LangChain adapter in Phase 2

3. **How to handle very long workflows (>1 hour)?**
   - Current design assumes workflows complete quickly
   - For long workflows, need checkpointing
   - **Decision:** Document "workflows should complete in <10 min" as design constraint

4. **Should we support streaming?**
   - Useful for UI previews
   - Adds complexity to evaluation
   - **Decision:** Defer to post-MVP (batch experiments don't need streaming)

---

## Conclusion

This specification synthesizes the best ideas from:
- ✅ Original workflow optimizer design (Taguchi, multi-objective)
- ✅ Simplified HITL architecture (workflows-as-boundaries)
- ✅ Generation strategies as variables (VS is not special)
- ✅ ChatGPT's DOE best practices (Pareto, provider abstraction, ensembles)

**Result:** A general-purpose LLM workflow optimization framework that is:
- Simple (no complex orchestration)
- Efficient (Taguchi reduces experiments)
- Flexible (pluggable strategies, evaluators)
- Observable (Langfuse integration)
- Practical (Pareto shows real trade-offs)

**Next Steps:**
1. Review and refine this spec
2. Begin Week 1-2 implementation (core framework)
3. Extract BaseWorkflow from StoryPunk codebase
4. Build first example workflow (code review or scene drafting)

---

## Appendix A: Example End-to-End Flow

### Scenario: Optimize Code Review Workflow

**Step 1: Define Workflow**

```python
# workflows/code_review.py

class CodeReviewWorkflow(BaseWorkflowService[CodeReviewInput, CodeReviewOutput]):
    def _build_workflow(self) -> StateGraph:
        graph = StateGraph()
        graph.add_node("analyze", self._analyze_code)
        graph.add_node("suggest", self._generate_suggestions)
        graph.add_edge("analyze", "suggest")
        graph.set_entry_point("analyze")
        graph.set_finish_point("suggest")
        return graph.compile()

    async def _analyze_code(self, state: dict) -> dict:
        strategy = state["strategy"]
        prompt = self.config.render_prompt("analyze", {"code": state["input"]["code"]})
        analysis = await strategy.generate(prompt, self.model, self.config.dict())
        state["analysis"] = analysis
        return state
```

**Step 2: Define Experiment**

```yaml
# experiments/code_review_opt.yaml
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

test_cases:
  - input_file: "test_data/react_component.js"
```

**Step 3: Run Experiment**

```bash
llm-optimizer experiment run experiments/code_review_opt.yaml
```

**Output:**
```
Running Taguchi L8 experiment: code_review_optimization
8 tests across 4 variables

Test 1/8: temp=0.3, model=deepseek, context=file_only, strategy=standard
  Quality: 0.72, Cost: $0.02, Time: 1200ms, Utility: 0.68

Test 2/8: temp=0.3, model=deepseek, context=full_module, strategy=verbalized_sampling
  Quality: 0.78, Cost: $0.15, Time: 5800ms, Utility: 0.65

...

Test 8/8: temp=0.7, model=claude, context=full_module, strategy=verbalized_sampling
  Quality: 0.88, Cost: $0.25, Time: 6200ms, Utility: 0.72

Main Effects Analysis:
  temperature: 18% contribution (0.7 > 0.3)
  model: 22% contribution (claude > deepseek)
  context_size: 45% contribution (full_module >> file_only)
  generation_strategy: 15% contribution (verbalized_sampling > standard)

Optimal Configuration:
  temperature: 0.7
  model: anthropic/claude-3.5-sonnet
  context_size: full_module
  generation_strategy: verbalized_sampling

Pareto Frontier (5 configs):
  Config 8: Quality 0.88, Cost $0.25 ⭐ (Highest quality)
  Config 4: Quality 0.82, Cost $0.12 ⭐ (Best balance)
  Config 1: Quality 0.72, Cost $0.02 ⭐ (Lowest cost)

Results saved to: results/code_review_optimization/
Pareto plot: results/code_review_optimization/pareto.svg
```

**Step 4: Review Pareto Plot**

```
Quality Score
     1.0 ┤
         │
     0.9 ┤                    Config 8 ⭐
         │
     0.8 ┤          Config 4 ⭐
         │
     0.7 ┤ Config 1 ⭐
         │
     0.6 ┤
         └─────────────────────────────> Cost (USD)
           0.02   0.12              0.25
```

**Step 5: Deploy Optimal Config**

```yaml
# workflows/defaults/code_review.yaml (updated)
models:
  analyzer:
    model: "anthropic/claude-3.5-sonnet"
    temperature: 0.7
    generation_strategy: "verbalized_sampling"
    vs_k: 5

context_size: "full_module"
```

**Result:**
- ✅ Found optimal config via systematic experimentation
- ✅ Validated that VS improves quality (15% contribution)
- ✅ Discovered context_size is most important (45% contribution)
- ✅ Can choose from Pareto frontier based on budget (Config 4 for balance, Config 1 for cost)
