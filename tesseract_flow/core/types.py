"""Core shared types for TesseractFlow."""
from __future__ import annotations

from typing import Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field


ExperimentStatus = Literal["PENDING", "RUNNING", "COMPLETED", "FAILED"]


class RubricDimension(TypedDict):
    """Structure describing a rubric dimension used during evaluation."""

    description: str
    scale: str


class UtilityWeights(BaseModel):
    """Weights applied to quality, cost, and time when computing utility."""

    quality: float = Field(default=1.0, ge=0.0)
    cost: float = Field(default=0.1, ge=0.0)
    time: float = Field(default=0.05, ge=0.0)
    model_config = ConfigDict(frozen=True)
