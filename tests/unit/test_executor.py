from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pytest

from tesseract_flow.core.config import (
    ExperimentConfig,
    ExperimentMetadata,
    ExperimentRun,
    TestConfiguration,
    TestResult,
    UtilityWeights,
    Variable,
    WorkflowConfig,
)
from tesseract_flow.core.exceptions import ExperimentError
from tesseract_flow.evaluation.metrics import DimensionScore, QualityScore
from tesseract_flow.experiments.executor import ExperimentExecutor
from tesseract_flow.experiments.taguchi import generate_test_configs


class DummyWorkflowOutput:
    def __init__(self, *, evaluation_text: str, cost: float, latency_ms: float, metadata: Dict[str, Any] | None = None) -> None:
        self.evaluation_text = evaluation_text
        self.cost = cost
        self.latency_ms = latency_ms
        self.metadata = metadata or {}

    def render_for_evaluation(self) -> str:
        return self.evaluation_text


class StubWorkflowService:
    def __init__(self, outputs: List[DummyWorkflowOutput]) -> None:
        self._outputs = outputs
        self._index = 0
        self.last_run_metadata: Dict[str, Any] | None = None
        self.config = WorkflowConfig()

    def prepare_input(self, test_config: TestConfiguration, experiment_config: ExperimentConfig | None) -> Dict[str, Any]:
        return {"test_number": test_config.test_number, "config": test_config.config_values}

    def run(self, input_data: Dict[str, Any]) -> DummyWorkflowOutput:
        output = self._outputs[self._index]
        self._index += 1
        self.last_run_metadata = {"duration_seconds": output.latency_ms / 1000.0}
        return output


class StubEvaluator:
    def __init__(self) -> None:
        self.calls = 0

    async def evaluate(
        self,
        workflow_output: str,
        rubric: Dict[str, Any] | None = None,
        *,
        extra_instructions: str | None = None,
    ) -> QualityScore:
        self.calls += 1
        score = QualityScore(
            dimension_scores={"clarity": DimensionScore(score=0.8, reasoning="solid")},
            evaluator_model="stub-model",
        )
        return score.with_metadata(call=self.calls, rubric=rubric)


@pytest.fixture
def experiment_config() -> ExperimentConfig:
    variables = [
        Variable(name="temperature", level_1=0.3, level_2=0.7),
        Variable(name="model", level_1="gpt-4", level_2="claude"),
        Variable(name="context", level_1="file", level_2="module"),
        Variable(name="strategy", level_1="standard", level_2="cot"),
    ]
    return ExperimentConfig(
        name="executor_test",
        workflow="code_review",
        variables=variables,
        utility_weights=UtilityWeights(),
    )


def _quality_score(value: float) -> QualityScore:
    return QualityScore(
        dimension_scores={"clarity": DimensionScore(score=value, reasoning="")},
        evaluator_model="stub",
    )


@pytest.mark.asyncio
async def test_run_single_test_returns_result(experiment_config: ExperimentConfig) -> None:
    test_config = generate_test_configs(experiment_config)[0]
    outputs = [
        DummyWorkflowOutput(
            evaluation_text="Comprehensive review",
            cost=0.005,
            latency_ms=2100,
            metadata={"tokens": 1500},
        )
    ]
    service = StubWorkflowService(outputs)
    evaluator = StubEvaluator()

    executor = ExperimentExecutor(lambda workflow, config: service, evaluator)
    result = await executor.run_single_test(
        test_config,
        service,
        evaluator,
        experiment_config=experiment_config,
    )

    assert result.cost == pytest.approx(0.005)
    assert result.latency == pytest.approx(2100)
    assert "workflow" in result.metadata
    assert result.quality_score.overall_score == pytest.approx(0.8)
    assert result.metadata["evaluation"]["model"] == "stub-model"


@pytest.mark.asyncio
async def test_run_executes_all_tests_and_persists(
    experiment_config: ExperimentConfig, tmp_path: Path
) -> None:
    outputs = [
        DummyWorkflowOutput(
            evaluation_text=f"Review {index}",
            cost=0.001 * index,
            latency_ms=1500 + (index * 10),
            metadata={"index": index},
        )
        for index in range(1, 9)
    ]
    service = StubWorkflowService(outputs)
    evaluator = StubEvaluator()
    executor = ExperimentExecutor(lambda workflow, config: service, evaluator)

    progress: List[int] = []

    def track_progress(current: int, total: int) -> None:
        assert total == 8
        progress.append(current)

    output_path = tmp_path / "experiment_run.json"
    run = await executor.run(
        experiment_config,
        progress_callback=track_progress,
        persist_path=output_path,
    )

    assert run.status == "COMPLETED"
    assert len(run.results) == 8
    assert progress[0] == 0
    assert progress[-1] == 8
    assert output_path.exists()

    loaded = ExperimentExecutor.load_run(output_path)
    assert loaded.experiment_id == run.experiment_id
    assert len(loaded.results) == 8


@pytest.mark.asyncio
async def test_run_resumes_from_partial_state(
    experiment_config: ExperimentConfig, tmp_path: Path
) -> None:
    test_configs = generate_test_configs(experiment_config)
    base_run = ExperimentRun(
        experiment_id="resume-test",
        config=experiment_config,
        test_configurations=test_configs,
        experiment_metadata=ExperimentMetadata.from_config(
            experiment_config, dependencies={"pydantic": "2"}
        ),
    ).mark_running(started_at=datetime.now(tz=timezone.utc))

    first_result = TestResult(
        test_number=1,
        config=test_configs[0],
        quality_score=_quality_score(0.7),
        cost=0.004,
        latency=2000,
        workflow_output="First",
    )
    second_result = TestResult(
        test_number=2,
        config=test_configs[1],
        quality_score=_quality_score(0.75),
        cost=0.005,
        latency=2100,
        workflow_output="Second",
    )

    base_run = base_run.record_result(first_result)
    base_run = base_run.record_result(second_result)

    outputs = [
        DummyWorkflowOutput(
            evaluation_text=f"Resume {index}",
            cost=0.002 * index,
            latency_ms=1800 + (index * 5),
        )
        for index in range(3, 9)
    ]
    service = StubWorkflowService(outputs)
    evaluator = StubEvaluator()
    executor = ExperimentExecutor(lambda workflow, config: service, evaluator)

    resumed = await executor.run(
        experiment_config,
        resume_from=base_run,
        persist_path=tmp_path / "resume.json",
    )

    assert resumed.status == "COMPLETED"
    assert len(resumed.results) == 8
    assert resumed.experiment_id == "resume-test"
    assert resumed.results[0].utility != 0.0


@pytest.mark.asyncio
async def test_resume_rejects_mismatched_config(experiment_config: ExperimentConfig) -> None:
    test_configs = generate_test_configs(experiment_config)
    run = ExperimentRun(
        experiment_id="resume-fail",
        config=experiment_config,
        test_configurations=test_configs,
    )

    modified_config = experiment_config.model_copy(update={"name": "different"})
    executor = ExperimentExecutor(lambda workflow, config: StubWorkflowService([]), StubEvaluator())

    with pytest.raises(ExperimentError):
        await executor.run(modified_config, resume_from=run)

