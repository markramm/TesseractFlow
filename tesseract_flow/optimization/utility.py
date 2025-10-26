"""Utility calculations for balancing quality, cost, and latency."""
from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

from tesseract_flow.core.types import UtilityWeights


class UtilityFunction:
    """Compute weighted utility scores for experiment results."""

    def __init__(self, weights: UtilityWeights) -> None:
        self.weights = weights

    def compute(self, *, quality: float, cost: float, latency: float) -> float:
        """Compute utility using normalized cost and latency values."""

        return (
            self.weights.quality * quality
            - self.weights.cost * cost
            - self.weights.time * latency
        )

    @staticmethod
    def normalize_metrics(
        values: Sequence[float], method: str = "min-max"
    ) -> Tuple[List[float], dict[str, float]]:
        """Normalize metric values to the [0, 1] range."""

        if method != "min-max":
            msg = f"Unsupported normalization method: {method}"
            raise ValueError(msg)

        values_list = list(values)
        if not values_list:
            return [], {"min": 0.0, "max": 0.0}

        minimum = min(values_list)
        maximum = max(values_list)
        if maximum == minimum:
            return [0.0 for _ in values_list], {"min": minimum, "max": maximum}

        scale = maximum - minimum
        normalized = [(value - minimum) / scale for value in values_list]
        return normalized, {"min": minimum, "max": maximum}

    def compute_for_sequences(
        self,
        qualities: Iterable[float],
        costs: Sequence[float],
        latencies: Sequence[float],
    ) -> List[float]:
        """Compute utilities for aligned quality, cost, and latency sequences."""

        normalized_costs, _ = self.normalize_metrics(costs)
        normalized_latencies, _ = self.normalize_metrics(latencies)
        normalized_len = len(normalized_costs)
        if normalized_len != len(normalized_latencies):
            msg = "Cost and latency sequences must share the same length."
            raise ValueError(msg)

        quality_list = list(qualities)
        if len(quality_list) != normalized_len:
            msg = "Quality, cost, and latency sequences must be aligned."
            raise ValueError(msg)

        return [
            self.compute(quality=quality, cost=cost_norm, latency=latency_norm)
            for quality, cost_norm, latency_norm in zip(
                quality_list, normalized_costs, normalized_latencies
            )
        ]
