"""Unit tests for evaluation metrics models."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from tesseract_flow.evaluation.metrics import DimensionScore, QualityScore


def test_quality_score_computes_overall_mean() -> None:
    dimension_scores = {
        "clarity": DimensionScore(score=0.8, reasoning="Clear"),
        "accuracy": DimensionScore(score=0.6, reasoning="Minor mistakes"),
        "usefulness": DimensionScore(score=1.0, reasoning="Highly actionable"),
    }
    score = QualityScore(
        dimension_scores=dimension_scores,
        evaluator_model="anthropic/claude-3.5-sonnet",
        overall_score=0.0,  # Should be recalculated to the mean
    )
    expected_mean = (0.8 + 0.6 + 1.0) / 3
    assert score.overall_score == pytest.approx(expected_mean)


def test_quality_score_rejects_empty_dimensions() -> None:
    with pytest.raises(ValueError):
        QualityScore(
            dimension_scores={},
            evaluator_model="anthropic/claude-3.5-sonnet",
        )


def test_dimension_score_normalizes_reasoning_whitespace() -> None:
    score = DimensionScore(score=0.75, reasoning="  Detailed reasoning.  ")
    assert score.reasoning == "Detailed reasoning."


def test_quality_score_requires_model_identifier() -> None:
    dimension_scores = {"clarity": DimensionScore(score=0.9)}
    with pytest.raises(ValueError):
        QualityScore(dimension_scores=dimension_scores, evaluator_model="  ")


def test_quality_score_uses_utc_timestamp() -> None:
    dimension_scores = {"clarity": DimensionScore(score=0.9)}
    score = QualityScore(dimension_scores=dimension_scores, evaluator_model="test/model")
    assert score.timestamp.tzinfo is timezone.utc
    assert isinstance(score.timestamp, datetime)


def test_quality_score_rejects_blank_dimension_name() -> None:
    dimension_scores = {"   ": DimensionScore(score=0.5)}
    with pytest.raises(ValueError):
        QualityScore(dimension_scores=dimension_scores, evaluator_model="model/test")
