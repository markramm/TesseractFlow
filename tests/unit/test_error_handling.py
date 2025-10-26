"""Unit tests covering error handling and retry behaviour."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, Iterable

import pytest
from pydantic import BaseModel

from tesseract_flow.core.base_workflow import BaseWorkflowService
from tesseract_flow.core.config import (
    ExperimentConfig,
    TestConfiguration,
    UtilityWeights,
    Variable,
)
from tesseract_flow.core.exceptions import ConfigurationError, EvaluationError, ExperimentError
from tesseract_flow.evaluation.metrics import DimensionScore, QualityScore
from tesseract_flow.evaluation.rubric import RubricEvaluator
from tesseract_flow.experiments.executor import ExperimentExecutor


@pytest.mark.asyncio
async def test_rubric_evaluator_retries_before_success(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = 0

    async def failing_completion(**_: Any) -> Dict[str, Any]:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RuntimeError("temporary failure")
        payload = {
            dimension: {"score": 8, "reasoning": "ok"}
            for dimension in RubricEvaluator.DEFAULT_RUBRIC
        }
        return {"choices": [{"message": {"content": json.dumps(payload)}}]}

    async def no_sleep(_: float) -> None:  # pragma: no cover - deterministic stub
        return None

    monkeypatch.setattr(
        "tesseract_flow.evaluation.rubric.litellm.acompletion",
        failing_completion,
    )
    monkeypatch.setattr("tesseract_flow.evaluation.rubric.asyncio.sleep", no_sleep)
    monkeypatch.setattr("tesseract_flow.evaluation.rubric.random.uniform", lambda *_: 0.0)

    evaluator = RubricEvaluator(max_retries=3, retry_base_delay=0.1)
    score = await evaluator.evaluate("Example output")

    assert pytest.approx(score.overall_score, rel=1e-5) == 0.8
    assert attempts == 3


@pytest.mark.asyncio
async def test_rubric_evaluator_raises_after_max_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    async def always_fail(**_: Any) -> Dict[str, Any]:
        raise RuntimeError("boom")

    async def no_sleep(_: float) -> None:  # pragma: no cover - deterministic stub
        return None

    monkeypatch.setattr(
        "tesseract_flow.evaluation.rubric.litellm.acompletion",
        always_fail,
    )
    monkeypatch.setattr("tesseract_flow.evaluation.rubric.asyncio.sleep", no_sleep)
    monkeypatch.setattr("tesseract_flow.evaluation.rubric.random.uniform", lambda *_: 0.0)

    evaluator = RubricEvaluator(max_retries=2, retry_base_delay=0.01)

    with pytest.raises(EvaluationError) as exc_info:
        await evaluator.evaluate("Example output")

    assert "failed after 2 attempts" in str(exc_info.value)


def test_experiment_config_from_yaml_provides_error_details(tmp_path: Path) -> None:
    payload = {"name": "exp", "variables": []}
    path = tmp_path / "config.yaml"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ConfigurationError) as exc_info:
        ExperimentConfig.from_yaml(path)

    assert exc_info.value.details
    assert any("workflow" in detail.lower() for detail in exc_info.value.details)


def test_executor_persists_partial_results_on_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    variables = [
        Variable(name="temperature", level_1=0.1, level_2=0.9),
        Variable(name="model", level_1="gpt-4", level_2="claude"),
        Variable(name="context", level_1="file", level_2="module"),
        Variable(name="strategy", level_1="standard", level_2="cot"),
    ]
    config = ExperimentConfig(
        name="experiment",
        workflow="code_review",
        variables=variables,
        utility_weights=UtilityWeights(quality=1.0, cost=0.0, time=0.0),
    )

    def fake_generate(_: ExperimentConfig) -> list[TestConfiguration]:
        tests: list[TestConfiguration] = []
        for index in range(8):
            config_values = {var.name: var.level_1 for var in variables}
            if index % 2 == 1:
                config_values[variables[0].name] = variables[0].level_2
            tests.append(
                TestConfiguration(
                    test_number=index + 1,
                    workflow="code_review",
                    config_values=config_values,
                )
            )
        return tests

    monkeypatch.setattr(
        "tesseract_flow.experiments.executor.generate_test_configs",
        fake_generate,
    )

    class DummyOutput(BaseModel):
        review: str
        cost: float = 0.0
        latency_ms: float = 5.0

        def render_for_evaluation(self) -> str:
            return self.review

    class DummyWorkflow(BaseWorkflowService[TestConfiguration, DummyOutput]):
        def __init__(self, outputs: Iterable[str]) -> None:
            super().__init__()
            self._outputs = list(outputs)
            self._index = 0

        def _build_workflow(self) -> Any:  # type: ignore[override]
            workflow = self

            class _Graph:
                def compile(self_inner) -> DummyWorkflow:
                    return workflow

            return _Graph()

        def _validate_output(self, result: Any) -> DummyOutput:
            return DummyOutput(review=result)

        # BaseWorkflowService expects compiled graph with invoke method.
        def invoke(self, payload: Dict[str, Any]) -> str:  # type: ignore[override]
            value = self._outputs[self._index]
            self._index += 1
            return value

    class FakeEvaluator:
        def __init__(self) -> None:
            self.calls = 0

        async def evaluate(self, *_: Any, **__: Any) -> QualityScore:
            self.calls += 1
            if self.calls == 2:
                raise EvaluationError("forced failure")
            return QualityScore(
                dimension_scores={
                    "clarity": DimensionScore(score=0.7, reasoning="ok"),
                },
                evaluator_model="test-model",
            )

    outputs = [f"Run {idx}" for idx in range(8)]
    workflow = DummyWorkflow(outputs)

    def resolver(_: str, __: ExperimentConfig) -> DummyWorkflow:
        return workflow

    executor = ExperimentExecutor(resolver, FakeEvaluator())

    persist_path = tmp_path / "partial_results.json"

    with pytest.raises(ExperimentError):
        asyncio.run(
            executor.run(
                config,
                persist_path=persist_path,
            )
        )

    assert persist_path.exists()
    run_state = ExperimentExecutor.load_run(persist_path)
    assert run_state.status == "FAILED"
    assert len(run_state.results) == 1
    assert run_state.error == "forced failure"

