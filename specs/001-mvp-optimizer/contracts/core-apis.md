# Core API Contracts

**Feature**: 001-mvp-optimizer | **Date**: 2025-10-25

This document specifies the internal Python APIs for TesseractFlow core modules.

---

## Module: `tesseract_flow.experiments.taguchi`

### `generate_l8_array`

Generate L8 Taguchi orthogonal array for given number of variables.

```python
def generate_l8_array(num_variables: int) -> np.ndarray:
    """
    Generate L8 orthogonal array.

    Args:
        num_variables: Number of variables (4-7)

    Returns:
        8x(num_variables) array with values {1, 2}

    Raises:
        ValueError: If num_variables not in range [4, 7]

    Example:
        >>> array = generate_l8_array(4)
        >>> array.shape
        (8, 4)
        >>> set(array.flatten())
        {1, 2}
    """
```

### `generate_test_configs`

Map L8 array to test configurations.

```python
def generate_test_configs(
    variables: List[Variable],
    workflow: str
) -> List[TestConfiguration]:
    """
    Generate 8 test configurations from variables.

    Args:
        variables: List of 4-7 Variable objects with level_1/level_2
        workflow: Workflow identifier

    Returns:
        List of 8 TestConfiguration objects

    Raises:
        ValueError: If len(variables) not in [4, 7]

    Example:
        >>> vars = [
        ...     Variable(name="temp", level_1=0.3, level_2=0.7),
        ...     Variable(name="model", level_1="gpt-4", level_2="claude"),
        ...     Variable(name="context", level_1="small", level_2="large"),
        ...     Variable(name="strategy", level_1="std", level_2="cot")
        ... ]
        >>> configs = generate_test_configs(vars, "code_review")
        >>> len(configs)
        8
        >>> configs[0].config_values["temp"]
        0.3  # First row of L8: all level 1
    """
```

---

## Module: `tesseract_flow.experiments.executor`

### `ExperimentExecutor.run`

Execute complete Taguchi L8 experiment.

```python
class ExperimentExecutor:
    async def run(
        self,
        config: ExperimentConfig,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> ExperimentRun:
        """
        Run all 8 tests in experiment.

        Args:
            config: Experiment configuration
            progress_callback: Optional callback(current, total) for progress

        Returns:
            Completed ExperimentRun with all results

        Raises:
            ExperimentError: If experiment execution fails

        Example:
            >>> executor = ExperimentExecutor()
            >>> config = ExperimentConfig.from_yaml("config.yaml")
            >>> run = await executor.run(config)
            >>> len(run.results)
            8
            >>> run.status
            ExperimentStatus.COMPLETED
        """
```

### `ExperimentExecutor.run_single_test`

Execute one test configuration.

```python
    async def run_single_test(
        self,
        test_config: TestConfiguration,
        workflow_service: BaseWorkflowService,
        evaluator: RubricEvaluator
    ) -> TestResult:
        """
        Run single test and evaluate result.

        Args:
            test_config: Configuration to test
            workflow_service: Workflow to execute
            evaluator: Quality evaluator

        Returns:
            TestResult with quality, cost, latency

        Example:
            >>> test = TestConfiguration(test_number=1, ...)
            >>> workflow = CodeReviewWorkflow()
            >>> evaluator = RubricEvaluator()
            >>> result = await executor.run_single_test(test, workflow, evaluator)
            >>> 0.0 <= result.quality_score.overall_score <= 1.0
            True
        """
```

---

## Module: `tesseract_flow.experiments.analysis`

### `MainEffectsAnalyzer.compute`

Compute main effects from experiment results.

```python
class MainEffectsAnalyzer:
    @staticmethod
    def compute(
        results: List[TestResult],
        variables: List[Variable]
    ) -> MainEffects:
        """
        Compute main effects for all variables.

        Args:
            results: 8 test results
            variables: Variables from experiment config

        Returns:
            MainEffects with contribution percentages

        Raises:
            ValueError: If len(results) != 8

        Example:
            >>> results = [...]  # 8 TestResult objects
            >>> vars = [...]  # 4 Variable objects
            >>> effects = MainEffectsAnalyzer.compute(results, vars)
            >>> sum(e.contribution_pct for e in effects.effects.values())
            100.0  # Approximately
        """
```

---

## Module: `tesseract_flow.evaluation.rubric`

### `RubricEvaluator.evaluate`

Evaluate workflow output using rubric.

```python
class RubricEvaluator:
    async def evaluate(
        self,
        workflow_output: str,
        rubric: Optional[Dict[str, RubricDimension]] = None,
        model: str = "anthropic/claude-3.5-sonnet",
        temperature: float = 0.3
    ) -> QualityScore:
        """
        Evaluate output using LLM-as-judge.

        Args:
            workflow_output: Text to evaluate
            rubric: Optional custom rubric (uses default if None)
            model: Evaluator model
            temperature: Sampling temperature (0.0-1.0)

        Returns:
            QualityScore with dimension scores and overall score

        Raises:
            EvaluationError: If LLM API call fails

        Example:
            >>> evaluator = RubricEvaluator()
            >>> output = "Code review: ..."
            >>> score = await evaluator.evaluate(output)
            >>> score.dimension_scores.keys()
            dict_keys(['clarity', 'accuracy', 'completeness', 'usefulness'])
            >>> 0.0 <= score.overall_score <= 1.0
            True
        """
```

---

## Module: `tesseract_flow.optimization.utility`

### `UtilityFunction.compute`

Calculate utility from quality, cost, latency.

```python
class UtilityFunction:
    def __init__(self, weights: UtilityWeights):
        self.weights = weights

    def compute(
        self,
        quality: float,
        cost: float,
        latency: float
    ) -> float:
        """
        Compute weighted utility score.

        Formula:
          utility = w_q × quality - w_c × norm(cost) - w_t × norm(latency)

        Args:
            quality: Quality score (0.0-1.0)
            cost: Cost in USD
            latency: Latency in milliseconds

        Returns:
            Utility score (unbounded, higher is better)

        Example:
            >>> weights = UtilityWeights(quality=1.0, cost=0.1, time=0.05)
            >>> utility_fn = UtilityFunction(weights)
            >>> utility = utility_fn.compute(quality=0.85, cost=0.005, latency=2000)
            >>> utility
            0.7856  # Approximately
        """
```

### `UtilityFunction.normalize_metrics`

Normalize cost and latency to 0-1 range.

```python
    @staticmethod
    def normalize_metrics(
        values: List[float],
        method: str = "min-max"
    ) -> List[float]:
        """
        Normalize values to [0, 1] range.

        Args:
            values: Raw metric values
            method: Normalization method ("min-max" or "z-score")

        Returns:
            Normalized values

        Example:
            >>> costs = [0.002, 0.005, 0.012, 0.008]
            >>> normalized = UtilityFunction.normalize_metrics(costs)
            >>> min(normalized), max(normalized)
            (0.0, 1.0)
        """
```

---

## Module: `tesseract_flow.optimization.pareto`

### `ParetoFrontier.compute`

Compute Pareto frontier from results.

```python
class ParetoFrontier:
    @staticmethod
    def compute(
        results: List[TestResult],
        x_axis: str = "cost",
        y_axis: str = "quality"
    ) -> ParetoFrontier:
        """
        Identify Pareto-optimal configurations.

        Args:
            results: Test results
            x_axis: Metric for X-axis (minimize)
            y_axis: Metric for Y-axis (maximize)

        Returns:
            ParetoFrontier with optimal points

        Example:
            >>> results = [...]  # 8 TestResult objects
            >>> frontier = ParetoFrontier.compute(results)
            >>> len(frontier.optimal_points)
            3  # Example: 3 non-dominated points
            >>> all(p.is_optimal for p in frontier.optimal_points)
            True
        """
```

### `ParetoFrontier.visualize`

Generate Pareto chart.

```python
    def visualize(
        self,
        output_path: Optional[Path] = None,
        show: bool = False,
        budget_threshold: Optional[float] = None
    ) -> Path:
        """
        Generate Pareto frontier visualization.

        Args:
            output_path: Save to file (PNG/SVG/PDF)
            show: Display interactive plot
            budget_threshold: Highlight points within budget

        Returns:
            Path to saved image

        Example:
            >>> frontier = ParetoFrontier.compute(results)
            >>> path = frontier.visualize(
            ...     output_path=Path("pareto.png"),
            ...     budget_threshold=0.01
            ... )
            >>> path.exists()
            True
        """
```

---

## Module: `tesseract_flow.core.base_workflow`

### `BaseWorkflowService`

Abstract base class for all workflows.

```python
class BaseWorkflowService(ABC, Generic[TInput, TOutput]):
    """
    Base class for LLM workflows.

    Type Parameters:
        TInput: Input schema (Pydantic model)
        TOutput: Output schema (Pydantic model)
    """

    def __init__(self, config: WorkflowConfig):
        self.config = config
        self.model = self._init_model()

    @abstractmethod
    async def execute(self, input_data: TInput) -> TOutput:
        """
        Execute workflow with given input.

        Args:
            input_data: Validated input

        Returns:
            Workflow output

        Raises:
            WorkflowError: If execution fails
        """

    @abstractmethod
    def _validate_output(self, result: Any) -> TOutput:
        """Validate and convert result to output schema."""
```

---

## Module: `tesseract_flow.core.strategies`

### `get_strategy`

Retrieve generation strategy by name.

```python
def get_strategy(name: str) -> GenerationStrategy:
    """
    Get generation strategy from registry.

    Args:
        name: Strategy name ("standard", "chain_of_thought", etc.)

    Returns:
        GenerationStrategy instance

    Raises:
        ValueError: If strategy not found

    Example:
        >>> strategy = get_strategy("standard")
        >>> result = await strategy.generate(prompt, model, config)
    """
```

### `register_strategy`

Register custom generation strategy.

```python
def register_strategy(name: str, strategy: GenerationStrategy) -> None:
    """
    Register custom strategy in global registry.

    Args:
        name: Strategy identifier
        strategy: Strategy implementation

    Example:
        >>> class MyStrategy:
        ...     async def generate(self, prompt, model, config):
        ...         return await model.ainvoke(prompt + "\\nThink carefully.")
        >>> register_strategy("my_strategy", MyStrategy())
    """
```

---

## Type Definitions

### Common Types

```python
# tesseract_flow/core/types.py

from typing import TypedDict, Literal

ExperimentStatus = Literal["PENDING", "RUNNING", "COMPLETED", "FAILED"]

class RubricDimension(TypedDict):
    description: str
    scale: str

class UtilityWeights(BaseModel):
    quality: float = 1.0
    cost: float = 0.1
    time: float = 0.05
```

---

## Error Hierarchy

```python
# tesseract_flow/core/exceptions.py

class TesseractFlowError(Exception):
    """Base exception for all TesseractFlow errors."""

class ConfigurationError(TesseractFlowError):
    """Invalid configuration."""

class ExperimentError(TesseractFlowError):
    """Experiment execution failed."""

class EvaluationError(TesseractFlowError):
    """Quality evaluation failed."""

class WorkflowError(TesseractFlowError):
    """Workflow execution failed."""

class VisualizationError(TesseractFlowError):
    """Visualization generation failed."""
```

---

## Testing Contracts

### Fixtures

```python
# tests/fixtures/experiment_fixtures.py

@pytest.fixture
def sample_variables() -> List[Variable]:
    """4 variables for testing."""
    return [
        Variable(name="temp", level_1=0.3, level_2=0.7),
        Variable(name="model", level_1="gpt-4", level_2="claude"),
        Variable(name="context", level_1="small", level_2="large"),
        Variable(name="strategy", level_1="std", level_2="cot")
    ]

@pytest.fixture
def sample_experiment_config(sample_variables) -> ExperimentConfig:
    """Complete experiment config."""
    return ExperimentConfig(
        name="test_experiment",
        workflow="code_review",
        variables=sample_variables,
        utility_weights=UtilityWeights(),
        seed=42
    )

@pytest.fixture
def sample_test_results() -> List[TestResult]:
    """8 test results with known properties."""
    # Returns results that sum to 100% contribution
    pass
```

### Test Categories

**Unit Tests:**
- `test_taguchi.py` - L8 array generation, orthogonality
- `test_main_effects.py` - Effect calculation, contribution %
- `test_utility.py` - Utility computation, normalization
- `test_pareto.py` - Frontier identification, dominance

**Integration Tests:**
- `test_experiment_flow.py` - End-to-end experiment execution
- `test_code_review.py` - Complete code review workflow

---

## Performance Contracts

### Time Budgets

| Operation | Max Duration |
|-----------|--------------|
| L8 array generation | <1ms |
| Test config generation | <10ms |
| Main effects computation | <100ms |
| Pareto frontier computation | <50ms |
| Visualization generation | <2s |
| Single test execution | <120s |
| Full L8 experiment (8 tests) | <15min |

### Memory Budgets

| Operation | Max Memory |
|-----------|------------|
| ExperimentRun object | <10MB |
| Visualization rendering | <50MB |

---

## Backward Compatibility

**Versioning:** Semantic versioning (MAJOR.MINOR.PATCH)

**Breaking changes** (require MAJOR bump):
- Changing TestConfiguration structure
- Removing required config fields
- Changing utility calculation formula

**Non-breaking changes** (MINOR bump):
- Adding optional config fields
- Adding new strategies
- Adding new visualization options

**Patches** (PATCH bump):
- Bug fixes
- Performance improvements
- Documentation updates
