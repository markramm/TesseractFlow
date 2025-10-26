# Research & Technical Decisions: LLM Workflow Optimizer MVP

**Feature**: 001-mvp-optimizer | **Date**: 2025-10-25
**Status**: Completed

This document captures research findings and technical decisions for unknowns identified in plan.md Phase 0.

---

## 1. Taguchi L8 Array Implementation

**Question**: What's the canonical L8 orthogonal array for 4-7 variables?

### Research Findings

The L8 (2^7) orthogonal array is a standard design that can accommodate up to 7 two-level factors in 8 experimental runs. It's based on a Hadamard matrix and ensures orthogonality (independence) between factors.

**Standard L8 Array:**

```
Test  V1  V2  V3  V4  V5  V6  V7
  1    1   1   1   1   1   1   1
  2    1   1   1   2   2   2   2
  3    1   2   2   1   1   2   2
  4    1   2   2   2   2   1   1
  5    2   1   2   1   2   1   2
  6    2   1   2   2   1   2   1
  7    2   2   1   1   2   2   1
  8    2   2   1   2   1   1   2
```

Where:
- V1-V7 = Variables (factors)
- 1 = Level 1 (low setting)
- 2 = Level 2 (high setting)

**Orthogonality Verification:**
- Each column has equal occurrences of 1 and 2 (four each)
- For any two columns, all four combinations (1,1), (1,2), (2,1), (2,2) occur exactly twice
- This ensures independent assessment of main effects

### Decision

**Implementation approach:**
1. Hard-code the L8 array as a NumPy array constant
2. Support 4-7 variables by using first N columns
3. Validate orthogonality in unit tests
4. Map array values (1,2) to actual configuration values from YAML

**Rationale:**
- L8 is standardized (no need to compute dynamically)
- NumPy provides efficient array operations
- Hard-coding is simpler and faster than generation algorithms
- Easy to extend to L16/L18 in future by adding more array constants

**Code structure:**
```python
# tesseract_flow/experiments/taguchi.py

import numpy as np

L8_ARRAY = np.array([
    [1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 2, 2, 2, 2],
    # ... (as shown above)
])

def generate_test_configs(variables: List[Variable]) -> List[TestConfig]:
    """
    Generate test configurations from L8 array.

    Args:
        variables: List of 4-7 variables with level_1 and level_2 values

    Returns:
        8 test configurations mapping array indices to variable values
    """
    num_vars = len(variables)
    if not 4 <= num_vars <= 7:
        raise ValueError("L8 supports 4-7 variables only")

    # Use first num_vars columns
    array_subset = L8_ARRAY[:, :num_vars]

    # Map 1→level_1, 2→level_2
    configs = []
    for row in array_subset:
        config = {}
        for var, level_idx in zip(variables, row):
            config[var.name] = var.level_1 if level_idx == 1 else var.level_2
        configs.append(TestConfig(**config))

    return configs
```

---

## 2. Main Effects Calculation

**Question**: How to compute main effects from Taguchi results?

### Research Findings

Main effects in Taguchi DOE measure how much each factor contributes to the response variable (in our case, utility). The calculation is:

**Effect of Factor A:**
- Average response when A is at Level 1: Ā₁
- Average response when A is at Level 2: Ā₂
- Main effect: E_A = Ā₂ - Ā₁

**Contribution Percentage:**
- Sum of squares for factor A: SS_A = (E_A)² × (number of observations at each level)
- Total sum of squares: SS_T = Σ(all SS_factors)
- Contribution %: (SS_A / SS_T) × 100

### Decision

**Algorithm:**
```python
# tesseract_flow/experiments/analysis.py

def compute_main_effects(results: List[TestResult],
                         variables: List[str]) -> MainEffects:
    """
    Compute main effects from experiment results.

    Args:
        results: 8 test results with utility scores
        variables: Variable names

    Returns:
        MainEffects with contribution percentages
    """
    effects = {}

    for var in variables:
        # Group results by variable level
        level_1_results = [r for r in results if r.config[var] == level_1_value]
        level_2_results = [r for r in results if r.config[var] == level_2_value]

        # Average utility at each level
        avg_1 = np.mean([r.utility for r in level_1_results])
        avg_2 = np.mean([r.utility for r in level_2_results])

        # Effect size and sum of squares
        effect = avg_2 - avg_1
        ss = (effect ** 2) * len(level_1_results)

        effects[var] = {
            'effect': effect,
            'avg_level_1': avg_1,
            'avg_level_2': avg_2,
            'sum_of_squares': ss
        }

    # Compute contribution percentages
    total_ss = sum(e['sum_of_squares'] for e in effects.values())
    for var in effects:
        effects[var]['contribution_pct'] = (effects[var]['sum_of_squares'] / total_ss) * 100

    return MainEffects(effects=effects, total_ss=total_ss)
```

**Rationale:**
- Standard Taguchi methodology (well-established)
- Simple to implement (no complex matrix operations)
- Contribution % is intuitive for users ("temperature matters 40%")
- Validates that contributions sum to ~100%

---

## 3. Pareto Frontier Algorithm

**Question**: Most efficient algorithm for 2D Pareto frontier?

### Research Findings

For 2D Pareto frontier (quality vs cost), the efficient algorithms are:
1. **Sort-based**: Sort by X, scan for non-dominated points - O(n log n)
2. **Divide-and-conquer**: Recursive approach - O(n log n)
3. **Brute-force**: Compare all pairs - O(n²) - simple but slow

For MVP with only 8 points, brute-force is acceptable. For production, sort-based is best.

### Decision

**Algorithm:** Sort-based for efficiency and simplicity

```python
# tesseract_flow/optimization/pareto.py

def compute_pareto_frontier(results: List[TestResult],
                           x_axis: str = 'cost',
                           y_axis: str = 'quality',
                           maximize_both: bool = False) -> List[ParetoPoint]:
    """
    Compute 2D Pareto frontier.

    Assumes: minimize cost (X), maximize quality (Y) by default

    Args:
        results: Test results with cost and quality
        x_axis: Metric for X-axis (default: 'cost')
        y_axis: Metric for Y-axis (default: 'quality')
        maximize_both: If True, maximize both axes

    Returns:
        List of Pareto-optimal points (non-dominated)
    """
    # Sort by X-axis (ascending for minimize, descending for maximize)
    sorted_results = sorted(results, key=lambda r: getattr(r, x_axis))

    pareto_points = []
    best_y = -float('inf') if not maximize_both else -float('inf')

    for result in sorted_results:
        y_val = getattr(result, y_axis)

        # For minimize cost, maximize quality:
        # A point is Pareto-optimal if its Y is better than previous best
        if y_val > best_y:
            pareto_points.append(ParetoPoint(
                config=result.config,
                cost=result.cost,
                quality=result.quality,
                latency=result.latency
            ))
            best_y = y_val

    return pareto_points
```

**Rationale:**
- O(n log n) complexity - efficient even for larger datasets
- Simple to understand and test
- Handles different optimization directions (min/max)
- For 8 points, performance is negligible anyway

**Alternatives considered:**
- `scipy.spatial.ConvexHull`: Overkill for 2D, designed for higher dimensions
- Custom divide-and-conquer: More complex, no performance benefit for small N

---

## 4. CLI Framework

**Question**: Click vs Typer for modern Python CLI?

### Research Findings

**Click:**
- Mature (10+ years), widely used
- Decorator-based, flexible
- No native type hints support (uses decorators)
- Async support requires extensions

**Typer:**
- Modern (built on Click)
- Native type hints (uses Python 3.6+ typing)
- Excellent Pydantic integration
- Built-in async support
- Better IDE autocomplete
- Automatic help generation from type hints

### Decision

**Use Typer** for CLI framework

**Rationale:**
- Type safety matches Pydantic config approach
- Better DX (developer experience) with IDE support
- Async support built-in (useful for LLM API calls)
- Still based on Click (stable foundation)
- Future-proof (modern Python patterns)

**Example structure:**
```python
# tesseract_flow/cli/main.py

import typer
from pathlib import Path
from typing import Optional

app = typer.Typer()

@app.command()
def run(
    config: Path = typer.Argument(..., help="Path to experiment config YAML"),
    output: Optional[Path] = typer.Option(None, help="Output JSON file"),
    verbose: bool = typer.Option(False, "--verbose", "-v")
):
    """Run a Taguchi L8 experiment."""
    # Implementation
    pass

@app.command()
def analyze(
    results: Path = typer.Argument(..., help="Path to results JSON"),
    show_chart: bool = typer.Option(True, help="Display main effects chart")
):
    """Analyze experiment results and show main effects."""
    # Implementation
    pass

if __name__ == "__main__":
    app()
```

---

## 5. LLM-as-Judge Best Practices

**Question**: How to minimize bias in rubric-based evaluation?

### Research Findings

Recent research (2024) on LLM-as-judge reliability:

**Key findings:**
- **Temperature**: Use 0.3-0.5 for consistent evaluations (not 0.0 - too deterministic, not 1.0 - too random)
- **Model choice**: Larger models (GPT-4, Claude 3.5) more reliable than smaller models
- **Prompt structure**: Chain-of-thought + rubric + numerical scale reduces bias
- **Bias mitigation**:
  - Provide reference examples (anchoring)
  - Use multiple dimensions (not single score)
  - Blind evaluation (don't reveal which config is which)
  - Consider pairwise comparison for critical decisions

### Decision

**Rubric-based evaluator design:**

```python
# tesseract_flow/evaluation/rubric.py

class RubricEvaluator:
    """
    LLM-as-judge evaluator using structured rubric.
    """

    DEFAULT_RUBRIC = {
        'clarity': {
            'description': 'Is the output clear and understandable?',
            'scale': '1-10 where 1=incomprehensible, 10=crystal clear'
        },
        'accuracy': {
            'description': 'Is the output factually accurate?',
            'scale': '1-10 where 1=many errors, 10=fully accurate'
        },
        'completeness': {
            'description': 'Does the output address all requirements?',
            'scale': '1-10 where 1=missing major parts, 10=comprehensive'
        },
        'usefulness': {
            'description': 'Is the output actionable and useful?',
            'scale': '1-10 where 1=not useful, 10=highly actionable'
        }
    }

    async def evaluate(self,
                      workflow_output: str,
                      rubric: Optional[Dict] = None,
                      model: str = "anthropic/claude-3.5-sonnet",
                      temperature: float = 0.3) -> QualityScore:
        """
        Evaluate workflow output using rubric.

        Returns QualityScore with dimension scores and overall score.
        """
        rubric = rubric or self.DEFAULT_RUBRIC

        prompt = self._build_evaluation_prompt(workflow_output, rubric)

        # Use LiteLLM for provider-agnostic call
        response = await litellm.acompletion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            response_format={"type": "json_object"}  # Structured output
        )

        scores = self._parse_scores(response)
        return QualityScore(
            dimension_scores=scores,
            overall_score=np.mean(list(scores.values()))
        )

    def _build_evaluation_prompt(self, output: str, rubric: Dict) -> str:
        """Build chain-of-thought evaluation prompt."""
        return f"""Evaluate the following output using this rubric. Think step-by-step.

OUTPUT TO EVALUATE:
{output}

RUBRIC:
{self._format_rubric(rubric)}

INSTRUCTIONS:
1. For each dimension, explain your reasoning
2. Assign a score based on the scale
3. Be objective and consistent

Respond in JSON format:
{{
  "clarity": {{"score": X, "reasoning": "..."}},
  "accuracy": {{"score": X, "reasoning": "..."}},
  ...
}}
"""
```

**Rationale:**
- Temperature 0.3 balances consistency with nuance
- Chain-of-thought improves reasoning transparency
- Multiple dimensions reduce single-score bias
- JSON structured output for reliable parsing
- Provider-agnostic via LiteLLM

**Future enhancements (post-MVP):**
- Pairwise comparison mode for critical decisions
- Ensemble evaluation (multiple models vote)
- Reference examples (few-shot evaluation)

---

## Summary of Decisions

| Research Area | Decision | Rationale |
|---------------|----------|-----------|
| **L8 Array** | Hard-coded NumPy constant | Standard, fast, simple, testable |
| **Main Effects** | Standard Taguchi formula | Well-established, intuitive contribution % |
| **Pareto** | Sort-based O(n log n) | Efficient, simple, handles edge cases |
| **CLI** | Typer (not Click) | Type safety, Pydantic integration, modern |
| **LLM Judge** | Rubric + CoT, temp=0.3 | Research-backed, reduces bias, explainable |

All decisions support the MVP goals: simplicity, correctness, performance, and transparency.

---

## Next Steps

**Phase 1 artifacts ready to generate:**
- ✅ data-model.md (entities and relationships)
- ✅ contracts/ (CLI commands, internal APIs)
- ✅ quickstart.md (test scenarios)

All research questions resolved. No blocking unknowns remain.
