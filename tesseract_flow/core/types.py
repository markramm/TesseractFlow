"""Core shared types for TesseractFlow."""
from __future__ import annotations

from typing import Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field


ExperimentStatus = Literal["PENDING", "RUNNING", "COMPLETED", "FAILED"]


class RubricDimension(TypedDict, total=False):
    """Structure describing a rubric dimension used during evaluation.

    Required fields:
        description: Brief description of what this dimension measures
        scale: The scoring scale (e.g., "1-5 where..." or "0-100 points")

    Optional fields:
        anchor_points: Dict mapping score levels to concrete criteria
                      (e.g., {"5_excellent": "...", "3_fair": "...", "1_inadequate": "..."})
        weight: Relative importance of this dimension (default: 1.0)
    """

    description: str
    scale: str
    anchor_points: dict[str, str]  # Optional: e.g., {"5_excellent": "criteria...", "1_poor": "..."}
    weight: float  # Optional: relative importance (default 1.0)


class UtilityWeights(BaseModel):
    """Weights applied to quality, cost, and time when computing utility."""

    quality: float = Field(default=1.0, ge=0.0)
    cost: float = Field(default=0.1, ge=0.0)
    time: float = Field(default=0.05, ge=0.0)
    model_config = ConfigDict(frozen=True)
