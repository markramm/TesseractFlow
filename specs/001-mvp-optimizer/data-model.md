# Data Model: LLM Workflow Optimizer MVP

**Feature**: 001-mvp-optimizer | **Date**: 2025-10-25
**Status**: Complete

This document defines the core data entities, their relationships, and validation rules.

---

## Entity Diagram

```
ExperimentConfig
    │
    ├──> Variable (1..7)
    │       └──> level_1: Any
    │       └──> level_2: Any
    │
    └──> WorkflowConfig
            └──> prompts, models, etc.

ExperimentConfig ──generates──> ExperimentRun
                                    │
                                    ├──> TestConfiguration (8)
                                    │       └──> config_values: Dict
                                    │
                                    └──> TestResult (8)
                                            ├──> quality: QualityScore
                                            ├──> cost: float
                                            ├──> latency: float
                                            └──> utility: float

TestResult[] ──analyzes──> MainEffects
                              └──> effects: Dict[var, Effect]

TestResult[] ──computes──> ParetoFrontier
                              └──> points: List[ParetoPoint]
```

---

## Core Entities

### 1. Variable

A parameter to optimize with two discrete levels.

**Fields:**
- `name: str` - Variable identifier (e.g., "temperature", "model")
- `level_1: Any` - Low/baseline setting (e.g., 0.3, "gpt-4")
- `level_2: Any` - High/alternative setting (e.g., 0.7, "claude-3.5")

**Validation:**
- name must be non-empty, alphanumeric + underscores
- level_1 and level_2 must be different
- Types of level_1 and level_2 should match (both str, or both float, etc.)

**Example:**
```yaml
temperature:
  level_1: 0.3
  level_2: 0.7

model:
  level_1: "openai/gpt-4"
  level_2: "anthropic/claude-3.5-sonnet"
```

---

### 2. ExperimentConfig

Configuration for a Taguchi L8 experiment.

**Fields:**
- `name: str` - Experiment name
- `workflow: str` - Workflow identifier (e.g., "code_review")
- `variables: List[Variable]` - 4-7 variables to test
- `utility_weights: UtilityWeights` - Quality/cost/time weights
- `workflow_config: Dict[str, Any]` - Workflow-specific configuration
- `seed: Optional[int]` - Random seed for reproducibility

**Nested: UtilityWeights:**
- `quality: float` - Weight for quality score (default: 1.0)
- `cost: float` - Weight for cost penalty (default: 0.1)
- `time: float` - Weight for latency penalty (default: 0.05)

**Validation:**
- 4 ≤ len(variables) ≤ 7 (L8 array constraint)
- All variable names must be unique
- Utility weights must be non-negative
- workflow must reference a valid WorkflowService

**Example:**
```yaml
name: "code_review_optimization"
workflow: "code_review"
variables:
  - name: "temperature"
    level_1: 0.3
    level_2: 0.7
  - name: "model"
    level_1: "openai/gpt-4"
    level_2: "anthropic/claude-3.5-sonnet"
  - name: "context_size"
    level_1: "file_only"
    level_2: "full_module"
  - name: "generation_strategy"
    level_1: "standard"
    level_2: "chain_of_thought"
utility_weights:
  quality: 1.0
  cost: 0.1
  time: 0.05
seed: 42
```

---

### 3. TestConfiguration

One specific combination of variable values from the L8 array.

**Fields:**
- `test_number: int` - 1-8 (row in L8 array)
- `config_values: Dict[str, Any]` - Variable name → level value
- `workflow: str` - Workflow identifier

**Validation:**
- 1 ≤ test_number ≤ 8
- config_values keys must match variable names
- All values must be either level_1 or level_2 from corresponding Variable

**Example:**
```python
TestConfiguration(
    test_number=1,
    config_values={
        "temperature": 0.3,
        "model": "openai/gpt-4",
        "context_size": "file_only",
        "generation_strategy": "standard"
    },
    workflow="code_review"
)
```

---

### 4. QualityScore

Evaluation result from rubric-based scoring.

**Fields:**
- `dimension_scores: Dict[str, DimensionScore]` - Scores by dimension
- `overall_score: float` - Average across dimensions (0.0-1.0)
- `evaluator_model: str` - Model used for evaluation
- `timestamp: datetime` - When evaluated

**Nested: DimensionScore:**
- `score: float` - 0.0-1.0 (normalized from 1-10 scale)
- `reasoning: Optional[str]` - Chain-of-thought explanation

**Validation:**
- All scores must be 0.0 ≤ score ≤ 1.0
- overall_score = mean(dimension_scores)
- dimension_scores must not be empty

**Example:**
```python
QualityScore(
    dimension_scores={
        "clarity": DimensionScore(score=0.8, reasoning="Clear structure..."),
        "accuracy": DimensionScore(score=0.9, reasoning="No factual errors..."),
        "completeness": DimensionScore(score=0.7, reasoning="Missing edge cases..."),
        "usefulness": DimensionScore(score=0.85, reasoning="Actionable suggestions...")
    },
    overall_score=0.8125,
    evaluator_model="anthropic/claude-3.5-sonnet",
    timestamp=datetime.now()
)
```

---

### 5. TestResult

Result from executing one test configuration.

**Fields:**
- `test_number: int` - References TestConfiguration
- `config: TestConfiguration` - The configuration tested
- `quality_score: QualityScore` - Evaluation result
- `cost: float` - USD spent on LLM API calls
- `latency: float` - Milliseconds from start to finish
- `utility: float` - Calculated utility score
- `workflow_output: str` - Raw workflow output
- `metadata: Dict[str, Any]` - Additional tracking data
- `timestamp: datetime` - When test ran

**Computed Fields:**
- `utility` - Calculated from quality, cost, latency using UtilityWeights

**Validation:**
- cost ≥ 0
- latency ≥ 0
- 0.0 ≤ quality_score.overall_score ≤ 1.0
- utility is recomputed if weights change

**Example:**
```python
TestResult(
    test_number=1,
    config=TestConfiguration(...),
    quality_score=QualityScore(...),
    cost=0.0042,  # $0.0042
    latency=2340.5,  # 2.34 seconds
    utility=0.7856,  # Computed
    workflow_output="...",
    metadata={"tokens_used": 1500, "provider": "openai"},
    timestamp=datetime.now()
)
```

---

### 6. ExperimentRun

Complete execution of an L8 experiment.

**Fields:**
- `experiment_id: str` - Unique identifier (UUID)
- `config: ExperimentConfig` - Experiment configuration
- `test_configurations: List[TestConfiguration]` - 8 configs from L8 array
- `results: List[TestResult]` - Results (may be partial if in-progress)
- `status: ExperimentStatus` - PENDING | RUNNING | COMPLETED | FAILED
- `started_at: datetime` - When experiment started
- `completed_at: Optional[datetime]` - When finished
- `error: Optional[str]` - Error message if FAILED

**Validation:**
- len(test_configurations) == 8
- len(results) ≤ 8
- status = COMPLETED only if len(results) == 8
- completed_at only set if status != PENDING | RUNNING

**Example:**
```python
ExperimentRun(
    experiment_id="exp_20251025_001",
    config=ExperimentConfig(...),
    test_configurations=[...],  # 8 configs
    results=[...],  # 0-8 results
    status=ExperimentStatus.RUNNING,
    started_at=datetime.now(),
    completed_at=None,
    error=None
)
```

---

### 7. Effect

Main effect for one variable.

**Fields:**
- `variable: str` - Variable name
- `effect_size: float` - Difference between level 2 and level 1 average utility
- `avg_level_1: float` - Average utility at level 1
- `avg_level_2: float` - Average utility at level 2
- `sum_of_squares: float` - SS for contribution calculation
- `contribution_pct: float` - Percentage contribution to total variance

**Validation:**
- effect_size = avg_level_2 - avg_level_1
- sum_of_squares ≥ 0
- contribution_pct ≥ 0

**Example:**
```python
Effect(
    variable="temperature",
    effect_size=0.12,  # Higher temp improves utility by 0.12
    avg_level_1=0.68,  # Average utility at temp=0.3
    avg_level_2=0.80,  # Average utility at temp=0.7
    sum_of_squares=0.0576,
    contribution_pct=35.2  # Temperature contributes 35.2%
)
```

---

### 8. MainEffects

Analysis of all variable effects.

**Fields:**
- `effects: Dict[str, Effect]` - Effect for each variable
- `total_ss: float` - Total sum of squares
- `experiment_id: str` - References ExperimentRun

**Validation:**
- sum(e.contribution_pct for e in effects.values()) ≈ 100.0
- len(effects) == number of variables in experiment

**Example:**
```python
MainEffects(
    effects={
        "temperature": Effect(effect_size=0.12, contribution_pct=35.2),
        "model": Effect(effect_size=0.08, contribution_pct=23.1),
        "context_size": Effect(effect_size=0.10, contribution_pct=28.5),
        "generation_strategy": Effect(effect_size=0.05, contribution_pct=13.2)
    },
    total_ss=0.1637,
    experiment_id="exp_20251025_001"
)
```

---

### 9. ParetoPoint

A configuration on the Pareto frontier.

**Fields:**
- `config: TestConfiguration` - The configuration
- `quality: float` - Quality score
- `cost: float` - Cost in USD
- `latency: float` - Latency in ms
- `is_optimal: bool` - True if on Pareto frontier
- `dominated_by: Optional[int]` - Test number that dominates this point (if any)

**Validation:**
- is_optimal = True if no other point has both higher quality AND lower cost
- If dominated_by is set, is_optimal must be False

**Example:**
```python
ParetoPoint(
    config=TestConfiguration(test_number=3, ...),
    quality=0.85,
    cost=0.005,
    latency=2500,
    is_optimal=True,
    dominated_by=None
)
```

---

### 10. ParetoFrontier

Set of Pareto-optimal configurations.

**Fields:**
- `points: List[ParetoPoint]` - All evaluated points (8 from experiment)
- `optimal_points: List[ParetoPoint]` - Subset that are Pareto-optimal
- `x_axis: str` - Metric on X-axis (default: "cost")
- `y_axis: str` - Metric on Y-axis (default: "quality")
- `experiment_id: str` - References ExperimentRun

**Validation:**
- All points in optimal_points must have is_optimal = True
- optimal_points ⊆ points
- len(optimal_points) ≥ 1 (at least one point is Pareto-optimal)

**Example:**
```python
ParetoFrontier(
    points=[...],  # All 8 test points
    optimal_points=[
        ParetoPoint(quality=0.75, cost=0.002, is_optimal=True),
        ParetoPoint(quality=0.85, cost=0.005, is_optimal=True),
        ParetoPoint(quality=0.90, cost=0.012, is_optimal=True)
    ],
    x_axis="cost",
    y_axis="quality",
    experiment_id="exp_20251025_001"
)
```

---

## Relationships

### One-to-Many
- ExperimentConfig → TestConfiguration (1:8)
- ExperimentConfig → Variable (1:4..7)
- ExperimentRun → TestResult (1:8)

### One-to-One
- TestResult → TestConfiguration (1:1)
- TestResult → QualityScore (1:1)
- ExperimentRun → MainEffects (1:1)
- ExperimentRun → ParetoFrontier (1:1)

### Computed Relationships
- MainEffects computes from TestResult[] (read-only)
- ParetoFrontier computes from TestResult[] (read-only)

---

## State Transitions

### ExperimentRun Status Flow

```
PENDING
   ↓
RUNNING ──┐
   ↓      │ (on error)
COMPLETED │
   ↑      ↓
   └── FAILED
```

**Valid transitions:**
- PENDING → RUNNING (start experiment)
- RUNNING → COMPLETED (all 8 tests done)
- RUNNING → FAILED (error during execution)
- FAILED → RUNNING (retry)

**Invariants:**
- PENDING: results = []
- RUNNING: 0 < len(results) < 8
- COMPLETED: len(results) == 8, completed_at is set
- FAILED: error is set

---

## Persistence Format

**MVP Storage:** JSON files (no database)

**File Structure:**
```
experiments/
├── exp_20251025_001/
│   ├── config.json              # ExperimentConfig
│   ├── test_configs.json        # TestConfiguration[] (8)
│   ├── results.json             # TestResult[] (0-8, grows during run)
│   ├── main_effects.json        # MainEffects (computed after completion)
│   └── pareto_frontier.json     # ParetoFrontier (computed after completion)
└── exp_20251025_002/
    └── ...
```

**JSON Serialization:**
- Pydantic models → `model.model_dump_json()`
- Datetimes → ISO 8601 strings
- Config values → preserve types (str, float, int, bool)

---

## Validation Rules Summary

| Entity | Key Validation |
|--------|----------------|
| Variable | level_1 ≠ level_2, types match |
| ExperimentConfig | 4 ≤ variables ≤ 7, unique names |
| TestConfiguration | Values are level_1 or level_2 from Variable |
| QualityScore | 0 ≤ scores ≤ 1, overall = mean(dimensions) |
| TestResult | cost ≥ 0, latency ≥ 0 |
| ExperimentRun | len(test_configs) == 8, status transitions valid |
| MainEffects | Contributions sum to ~100% |
| ParetoFrontier | optimal_points have is_optimal=True |

All validations enforced via Pydantic validators in `tesseract_flow/core/config.py` and entity modules.
