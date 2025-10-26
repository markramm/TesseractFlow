"""Integration tests for the rubric evaluator."""
from __future__ import annotations

import json
from typing import Any, Dict

import pytest

from tesseract_flow.core.exceptions import EvaluationError
from tesseract_flow.core.types import RubricDimension
from tesseract_flow.evaluation.rubric import RubricEvaluator


@pytest.mark.asyncio
async def test_rubric_evaluator_parses_litellm_response(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_kwargs: Dict[str, Any] = {}

    async def fake_acompletion(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        captured_kwargs.update(kwargs)
        payload = {
            "clarity": {"score": "9", "reasoning": "Clear messaging."},
            "accuracy": {"score": 8, "reasoning": "Minor nitpicks."},
            "completeness": {"score": 7.5, "reasoning": "Covers most areas."},
            "usefulness": {"score": 10, "reasoning": "Extremely actionable."},
        }
        return {"choices": [{"message": {"content": json.dumps(payload)}}]}

    monkeypatch.setattr(
        "tesseract_flow.evaluation.rubric.litellm.acompletion",
        fake_acompletion,
    )

    custom_rubric: Dict[str, RubricDimension] = {
        "clarity": RubricEvaluator.DEFAULT_RUBRIC["clarity"],
        "accuracy": RubricEvaluator.DEFAULT_RUBRIC["accuracy"],
        "completeness": RubricEvaluator.DEFAULT_RUBRIC["completeness"],
        "usefulness": RubricEvaluator.DEFAULT_RUBRIC["usefulness"],
    }

    evaluator = RubricEvaluator(model="test/model", temperature=0.4)
    score = await evaluator.evaluate(
        "Final workflow output",
        rubric=custom_rubric,
        temperature=0.2,
        extra_instructions="Highlight security issues first.",
    )

    assert score.evaluator_model == "test/model"
    assert score.overall_score == pytest.approx((0.9 + 0.8 + 0.75 + 1.0) / 4)
    assert score.dimension_scores["usefulness"].score == pytest.approx(1.0)
    assert "raw_response" in score.metadata
    assert score.metadata["temperature"] == 0.2
    assert score.metadata["rubric"] == custom_rubric

    assert captured_kwargs["model"] == "test/model"
    assert pytest.approx(captured_kwargs["temperature"]) == 0.2
    assert captured_kwargs["response_format"] == {"type": "json_object"}
    assert isinstance(captured_kwargs["messages"], list)


@pytest.mark.asyncio
async def test_rubric_evaluator_raises_on_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_acompletion(*args: Any, **kwargs: Any) -> Dict[str, Any]:  # pragma: no cover - trivial stub
        return {"choices": [{"message": {"content": "not-json"}}]}

    monkeypatch.setattr(
        "tesseract_flow.evaluation.rubric.litellm.acompletion",
        fake_acompletion,
    )

    evaluator = RubricEvaluator()
    with pytest.raises(EvaluationError):
        await evaluator.evaluate("Example output")
