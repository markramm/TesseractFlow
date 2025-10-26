import pytest

from tesseract_flow.core.types import UtilityWeights
from tesseract_flow.optimization.utility import UtilityFunction


def test_utility_function_compute_for_sequences_normalizes_values() -> None:
    weights = UtilityWeights(quality=1.0, cost=0.5, time=0.25)
    utility_fn = UtilityFunction(weights)

    qualities = [0.5, 0.75, 0.9]
    costs = [0.01, 0.02, 0.03]
    latencies = [1000, 1500, 2000]

    utilities = utility_fn.compute_for_sequences(qualities, costs, latencies)

    assert len(utilities) == 3
    normalized_costs, _ = UtilityFunction.normalize_metrics(costs)
    normalized_latencies, _ = UtilityFunction.normalize_metrics(latencies)
    expected = [
        weights.quality * q
        - weights.cost * cost
        - weights.time * latency
        for q, cost, latency in zip(qualities, normalized_costs, normalized_latencies)
    ]
    assert utilities == pytest.approx(expected)


def test_normalize_metrics_handles_constant_values() -> None:
    normalized, stats = UtilityFunction.normalize_metrics([0.5, 0.5, 0.5])
    assert normalized == [0.0, 0.0, 0.0]
    assert stats == {"min": 0.5, "max": 0.5}


def test_normalize_metrics_rejects_unknown_method() -> None:
    with pytest.raises(ValueError):
        UtilityFunction.normalize_metrics([1.0], method="z-score")
