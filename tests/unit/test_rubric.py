"""Unit tests for rubric evaluator utility methods."""
from __future__ import annotations

import json
from typing import Dict

import pytest

from tesseract_flow.core.exceptions import EvaluationError
from tesseract_flow.evaluation.rubric import RubricEvaluator


class _InMemoryCache:
    def __init__(self) -> None:
        self.store: Dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self.store.get(key)

    def set(self, key: str, value: str) -> None:
        self.store[key] = value

    def clear(self) -> None:  # pragma: no cover - helper API completeness
        self.store.clear()


def test_constructor_requires_model_identifier() -> None:
    with pytest.raises(ValueError):
        RubricEvaluator(model="   ")


@pytest.mark.asyncio
async def test_evaluate_requires_non_empty_output() -> None:
    evaluator = RubricEvaluator()
    with pytest.raises(EvaluationError):
        await evaluator.evaluate("   ")


@pytest.mark.asyncio
async def test_evaluate_requires_non_empty_model_override() -> None:
    evaluator = RubricEvaluator()
    with pytest.raises(EvaluationError):
        await evaluator.evaluate("valid output", model="  ")


def test_extract_response_content_requires_choices() -> None:
    evaluator = RubricEvaluator()
    with pytest.raises(EvaluationError):
        evaluator._extract_response_content({})  # type: ignore[arg-type]


def test_extract_response_content_requires_message() -> None:
    evaluator = RubricEvaluator()
    response = {"choices": [{}]}
    with pytest.raises(EvaluationError):
        evaluator._extract_response_content(response)


def test_extract_response_content_concatenates_list_parts() -> None:
    evaluator = RubricEvaluator()
    response = {
        "choices": [
            {
                "message": {
                    "content": [
                        {"text": "part 1 "},
                        {"text": "and part 2"},
                    ]
                }
            }
        ]
    }
    content = evaluator._extract_response_content(response)
    assert content == "part 1 and part 2"


def test_parse_dimension_scores_requires_all_dimensions() -> None:
    evaluator = RubricEvaluator()
    payload = {"clarity": {"score": 5}}
    rubric = {"clarity": RubricEvaluator.DEFAULT_RUBRIC["clarity"], "accuracy": RubricEvaluator.DEFAULT_RUBRIC["accuracy"]}
    with pytest.raises(EvaluationError):
        evaluator._parse_dimension_scores(payload, rubric)


def test_normalize_score_rejects_out_of_range_values() -> None:
    evaluator = RubricEvaluator()
    with pytest.raises(EvaluationError):
        evaluator._normalize_score(11)


def test_normalize_score_rejects_invalid_types() -> None:
    evaluator = RubricEvaluator()
    with pytest.raises(EvaluationError):
        evaluator._normalize_score(["not", "numeric"])  # type: ignore[arg-type]


def test_validate_temperature_bounds() -> None:
    evaluator = RubricEvaluator()
    with pytest.raises(ValueError):
        evaluator._validate_temperature(-0.1)
    with pytest.raises(ValueError):
        evaluator._validate_temperature(1.5)


def test_extract_response_content_supports_choice_objects() -> None:
    evaluator = RubricEvaluator()

    class _Message:
        def __init__(self, content: str) -> None:
            self.content = content

    class _Choice:
        def __init__(self, content: str) -> None:
            self.message = _Message(content)

    class _Response:
        def __init__(self, content: str) -> None:
            self.choices = [_Choice(content)]

    response = _Response("object based content")
    assert evaluator._extract_response_content(response) == "object based content"


def test_extract_response_content_requires_string_content() -> None:
    evaluator = RubricEvaluator()
    response = {"choices": [{"message": {"content": 123}}]}
    with pytest.raises(EvaluationError):
        evaluator._extract_response_content(response)


def test_parse_dimension_scores_accepts_numeric_entries() -> None:
    evaluator = RubricEvaluator()
    rubric = {"clarity": RubricEvaluator.DEFAULT_RUBRIC["clarity"]}
    payload = {"clarity": 8}
    scores = evaluator._parse_dimension_scores(payload, rubric)
    assert scores["clarity"].score == pytest.approx(0.8)


def test_normalize_score_accepts_unit_interval() -> None:
    evaluator = RubricEvaluator()
    assert evaluator._normalize_score(0.4) == pytest.approx(0.4)


def test_normalize_score_rejects_empty_string() -> None:
    evaluator = RubricEvaluator()
    with pytest.raises(EvaluationError):
        evaluator._normalize_score("   ")


def test_normalize_score_rejects_non_finite() -> None:
    evaluator = RubricEvaluator()
    with pytest.raises(EvaluationError):
        evaluator._normalize_score(float("nan"))

def test_normalize_score_rejects_non_finite_string() -> None:
    evaluator = RubricEvaluator()
    with pytest.raises(EvaluationError):
        evaluator._normalize_score("nan")


@pytest.mark.asyncio
async def test_evaluate_records_cache_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "clarity": {"score": 8, "reasoning": "Clear enough."},
        "accuracy": {"score": 7, "reasoning": "Mostly correct."},
        "completeness": {"score": 9, "reasoning": "Thorough."},
        "usefulness": {"score": 6, "reasoning": "Actionable."},
    }

    async def fake_acompletion(*args: object, **kwargs: object) -> dict[str, object]:
        return {"choices": [{"message": {"content": json.dumps(payload)}}]}

    monkeypatch.setattr(
        "tesseract_flow.evaluation.rubric.litellm.acompletion",
        fake_acompletion,
    )

    cache = _InMemoryCache()
    evaluator = RubricEvaluator(cache=cache, record_cache=True)
    score = await evaluator.evaluate("Example output")

    cache_key = score.metadata["cache_key"]
    assert cache.store[cache_key] == json.dumps(payload)
    assert score.metadata["cache_hit"] is False
    assert score.metadata["cache_recorded"] is True


@pytest.mark.asyncio
async def test_evaluate_uses_cached_response(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "clarity": {"score": 6, "reasoning": "Ok."},
        "accuracy": {"score": 6, "reasoning": "Ok."},
        "completeness": {"score": 6, "reasoning": "Ok."},
        "usefulness": {"score": 6, "reasoning": "Ok."},
    }

    cache = _InMemoryCache()
    cache.set("manual-key", json.dumps(payload))

    async def failing_acompletion(*args: object, **kwargs: object) -> dict[str, object]:
        raise AssertionError("LLM should not be invoked when cache is hit")

    monkeypatch.setattr(
        "tesseract_flow.evaluation.rubric.litellm.acompletion",
        failing_acompletion,
    )

    evaluator = RubricEvaluator(cache=cache)
    score = await evaluator.evaluate("Example output", use_cache=True, cache_key="manual-key")

    assert score.metadata["cache_hit"] is True
    assert "cache_recorded" not in score.metadata
    assert score.overall_score == pytest.approx(0.6)


@pytest.mark.asyncio
async def test_evaluate_requires_cache_backend_when_requested() -> None:
    evaluator = RubricEvaluator()
    with pytest.raises(EvaluationError):
        await evaluator.evaluate("Output", use_cache=True)
