"""Pareto frontier computation and visualization utilities."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from tesseract_flow.core.config import TestConfiguration, TestResult


_TOLERANCE = 1e-9


class ParetoPoint(BaseModel):
    """Represents a single configuration evaluated in an experiment."""

    config: TestConfiguration
    quality: float = Field(..., ge=0.0, le=1.0)
    cost: float = Field(..., ge=0.0)
    latency: float = Field(..., ge=0.0)
    utility: float
    is_optimal: bool = False
    dominated_by: Optional[int] = Field(default=None, ge=1, le=8)

    model_config = ConfigDict(frozen=True)

    @property
    def test_number(self) -> int:
        """Return the associated Taguchi test number."""

        return self.config.test_number

    @model_validator(mode="after")
    def _validate_dominance(self) -> "ParetoPoint":
        if self.dominated_by is not None and self.is_optimal:
            msg = "Pareto-optimal points cannot specify dominated_by."
            raise ValueError(msg)
        if self.dominated_by is not None and self.dominated_by == self.test_number:
            msg = "dominated_by cannot reference the same test number."
            raise ValueError(msg)
        return self


class ParetoFrontier(BaseModel):
    """Pareto frontier describing non-dominated experiment configurations."""

    experiment_id: str
    points: List[ParetoPoint]
    optimal_points: List[ParetoPoint]
    x_axis: str = "cost"
    y_axis: str = "quality"

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def _validate_frontier(self) -> "ParetoFrontier":
        if not self.points:
            msg = "At least one Pareto point is required."
            raise ValueError(msg)
        optimal_numbers = {point.test_number for point in self.optimal_points}
        if not optimal_numbers:
            msg = "At least one Pareto-optimal point must be present."
            raise ValueError(msg)
        for point in self.optimal_points:
            if not point.is_optimal:
                msg = "optimal_points must only contain optimal Pareto points."
                raise ValueError(msg)
        all_numbers = {point.test_number for point in self.points}
        if not optimal_numbers.issubset(all_numbers):
            msg = "optimal_points must be a subset of points."
            raise ValueError(msg)
        return self

    @staticmethod
    def compute(
        results: Sequence[TestResult],
        *,
        experiment_id: str,
        x_axis: str = "cost",
        y_axis: str = "quality",
    ) -> "ParetoFrontier":
        """Compute a Pareto frontier for the provided experiment *results*."""

        if not results:
            msg = "At least one TestResult is required to compute the Pareto frontier."
            raise ValueError(msg)

        axis_x = x_axis.strip().lower()
        axis_y = y_axis.strip().lower()

        valid_x = {"cost", "latency"}
        valid_y = {"quality", "utility"}
        if axis_x not in valid_x:
            msg = f"Unsupported x_axis '{x_axis}'. Expected one of: {sorted(valid_x)}."
            raise ValueError(msg)
        if axis_y not in valid_y:
            msg = f"Unsupported y_axis '{y_axis}'. Expected one of: {sorted(valid_y)}."
            raise ValueError(msg)

        raw_points: List[ParetoPoint] = []
        for result in results:
            point = ParetoPoint(
                config=result.config,
                quality=result.quality_score.overall_score,
                cost=result.cost,
                latency=result.latency,
                utility=result.utility,
            )
            raw_points.append(point)

        sorted_points = sorted(
            raw_points,
            key=lambda point: (
                _axis_value(point, axis_x),
                -_axis_value(point, axis_y),
            ),
        )

        optimal_numbers: List[int] = []
        best_y = float("-inf")
        for point in sorted_points:
            value_y = _axis_value(point, axis_y)
            if value_y > best_y + _TOLERANCE:
                best_y = value_y
                optimal_numbers.append(point.test_number)

        dominance_map = _compute_dominance(sorted_points, axis_x, axis_y)

        updated_points: List[ParetoPoint] = []
        for point in raw_points:
            test_number = point.test_number
            is_optimal = test_number in optimal_numbers
            dominated_by = dominance_map.get(test_number)
            updated_points.append(
                point.model_copy(update={"is_optimal": is_optimal, "dominated_by": dominated_by})
            )

        optimal_points = [point for point in updated_points if point.is_optimal]

        try:
            return ParetoFrontier(
                experiment_id=experiment_id,
                points=updated_points,
                optimal_points=optimal_points,
                x_axis=axis_x,
                y_axis=axis_y,
            )
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc

    def points_within_budget(self, budget: float) -> List[ParetoPoint]:
        """Return Pareto points whose X-axis value does not exceed *budget*."""

        if budget < 0:
            msg = "budget must be non-negative"
            raise ValueError(msg)
        return [
            point
            for point in self.points
            if _axis_value(point, self.x_axis) <= budget + _TOLERANCE
        ]

    def best_within_budget(self, budget: float) -> Optional[ParetoPoint]:
        """Return the highest-quality Pareto-optimal point within the given *budget*."""

        candidates = [
            point
            for point in self.optimal_points
            if _axis_value(point, self.x_axis) <= budget + _TOLERANCE
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda point: _axis_value(point, self.y_axis))

    def visualize(
        self,
        output_path: Optional[Path | str] = None,
        *,
        show: bool = False,
        budget_threshold: Optional[float] = None,
        title: Optional[str] = None,
    ) -> Path:
        """Generate a Pareto frontier chart and persist it to *output_path*."""

        destination = _resolve_output_path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)

        fig, ax = plt.subplots(figsize=(8, 6), dpi=120)

        sizes = _bubble_sizes([point.latency for point in self.points])
        size_lookup = {point.test_number: size for point, size in zip(self.points, sizes)}

        dominated = [point for point in self.points if not point.is_optimal]
        optimal = [point for point in self.points if point.is_optimal]

        if dominated:
            ax.scatter(
                [_axis_value(point, self.x_axis) for point in dominated],
                [_axis_value(point, self.y_axis) for point in dominated],
                s=[size_lookup[point.test_number] for point in dominated],
                c="#9ca3af",
                alpha=0.7,
                edgecolors="none",
                label="Dominated",
            )

        if optimal:
            ax.scatter(
                [_axis_value(point, self.x_axis) for point in optimal],
                [_axis_value(point, self.y_axis) for point in optimal],
                s=[size_lookup[point.test_number] for point in optimal],
                c="#2563eb",
                alpha=0.9,
                edgecolors="#1f2937",
                linewidths=0.8,
                label="Pareto-optimal",
            )

        for index, point in enumerate(self.points):
            ax.annotate(
                f"#{point.test_number}",
                (_axis_value(point, self.x_axis), _axis_value(point, self.y_axis)),
                textcoords="offset points",
                xytext=(6, 4),
                fontsize=9,
                color="#111827",
            )

        if budget_threshold is not None:
            ax.axvline(
                budget_threshold,
                color="#f59e0b",
                linestyle="--",
                linewidth=1.5,
                label=f"Budget ≤ {budget_threshold:.3f}",
            )

        ax.set_xlabel(_axis_label(self.x_axis))
        ax.set_ylabel(_axis_label(self.y_axis))
        chart_title = title or f"Pareto Frontier ({_axis_label(self.y_axis)} vs {_axis_label(self.x_axis)})"
        ax.set_title(chart_title)
        ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.5)
        ax.legend()

        fig.tight_layout()
        fig.savefig(destination, bbox_inches="tight")

        if show:
            plt.show()

        plt.close(fig)

        return destination


def _axis_value(point: ParetoPoint, axis: str) -> float:
    if axis == "cost":
        return point.cost
    if axis == "latency":
        return point.latency
    if axis == "quality":
        return point.quality
    if axis == "utility":
        return point.utility
    msg = f"Unsupported axis '{axis}'."
    raise ValueError(msg)


def _axis_label(axis: str) -> str:
    if axis == "cost":
        return "Cost (USD)"
    if axis == "latency":
        return "Latency (ms)"
    if axis == "quality":
        return "Quality Score"
    if axis == "utility":
        return "Utility"
    return axis.title()


def _compute_dominance(
    points: Sequence[ParetoPoint],
    axis_x: str,
    axis_y: str,
) -> dict[int, Optional[int]]:
    dominance: dict[int, Optional[int]] = {point.test_number: None for point in points}
    for point in points:
        for candidate in points:
            if point.test_number == candidate.test_number:
                continue
            dominates = (
                _axis_value(candidate, axis_x) <= _axis_value(point, axis_x) + _TOLERANCE
                and _axis_value(candidate, axis_y) >= _axis_value(point, axis_y) - _TOLERANCE
                and (
                    _axis_value(candidate, axis_x) < _axis_value(point, axis_x) - _TOLERANCE
                    or _axis_value(candidate, axis_y) > _axis_value(point, axis_y) + _TOLERANCE
                )
            )
            if dominates:
                dominance[point.test_number] = candidate.test_number
                break
    return dominance


def _bubble_sizes(latencies: Sequence[float]) -> List[float]:
    if not latencies:
        return []
    minimum = min(latencies)
    maximum = max(latencies)
    if maximum == minimum:
        return [300.0 for _ in latencies]
    span = maximum - minimum
    return [200.0 + ((latency - minimum) / span) * 600.0 for latency in latencies]


def _resolve_output_path(path: Optional[Path | str]) -> Path:
    if path is None:
        return Path("pareto_frontier.png")
    return Path(path)


__all__ = ["ParetoFrontier", "ParetoPoint"]
