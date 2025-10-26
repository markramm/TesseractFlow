"""Evaluation metrics and scoring models."""
from __future__ import annotations

from datetime import datetime, timezone
from statistics import fmean
from typing import Any, Dict, Mapping, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DimensionScore(BaseModel):
    """Score and rationale for a single evaluation rubric dimension."""

    score: float = Field(..., ge=0.0, le=1.0)
    reasoning: Optional[str] = None

    model_config = ConfigDict(frozen=True)

    @field_validator("reasoning")
    @classmethod
    def _normalize_reasoning(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class QualityScore(BaseModel):
    """Aggregated quality evaluation result across rubric dimensions."""

    dimension_scores: Dict[str, DimensionScore]
    overall_score: float = Field(default=0.0, ge=0.0, le=1.0)
    evaluator_model: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("dimension_scores")
    @classmethod
    def _validate_dimension_scores(
        cls, value: Mapping[str, DimensionScore]
    ) -> Dict[str, DimensionScore]:
        if not value:
            msg = "At least one dimension score must be provided."
            raise ValueError(msg)

        normalized: Dict[str, DimensionScore] = {}
        for name, score in value.items():
            key = name.strip()
            if not key:
                msg = "Dimension names must be non-empty strings."
                raise ValueError(msg)
            normalized[key] = score
        return normalized

    @field_validator("evaluator_model")
    @classmethod
    def _validate_model(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "Evaluator model identifier must be non-empty."
            raise ValueError(msg)
        return stripped

    @model_validator(mode="after")
    def _synchronize_overall(self) -> "QualityScore":
        scores = [dimension.score for dimension in self.dimension_scores.values()]
        mean_score = float(fmean(scores))
        object.__setattr__(self, "overall_score", mean_score)
        return self

    def with_metadata(self, **metadata: Any) -> "QualityScore":
        """Return a copy of the score with additional metadata merged in."""

        merged = {**self.metadata, **metadata}
        return self.model_copy(update={"metadata": merged})
