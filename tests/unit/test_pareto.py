from __future__ import annotations

from pathlib import Path

import pytest

from tesseract_flow.core.config import TestConfiguration, TestResult
from tesseract_flow.evaluation.metrics import DimensionScore, QualityScore
from tesseract_flow.optimization.pareto import ParetoFrontier


def _make_result(
    test_number: int,
    *,
    quality: float,
    cost: float,
    latency: float,
    workflow: str = "code_review",
    utility: float | None = None,
) -> TestResult:
    config = TestConfiguration(
        test_number=test_number,
        config_values={"model": "gpt"},
        workflow=workflow,
    )
    score = QualityScore(
        dimension_scores={"overall": DimensionScore(score=quality)},
        evaluator_model="test-model",
    )
    return TestResult(
        test_number=test_number,
        config=config,
        quality_score=score,
        cost=cost,
        latency=latency,
        utility=utility if utility is not None else quality,
        workflow_output="ok",
    )


def test_compute_pareto_frontier_identifies_optimal_points() -> None:
    results = [
        _make_result(1, quality=0.70, cost=0.002, latency=120.0),
        _make_result(2, quality=0.85, cost=0.004, latency=160.0),
        _make_result(3, quality=0.83, cost=0.003, latency=140.0),
        _make_result(4, quality=0.90, cost=0.006, latency=220.0),
        _make_result(5, quality=0.78, cost=0.005, latency=180.0),
    ]

    frontier = ParetoFrontier.compute(results, experiment_id="run-123")

    optimal_numbers = {point.test_number for point in frontier.optimal_points}
    assert optimal_numbers == {1, 2, 3, 4}

    dominated = {
        point.test_number: point.dominated_by
        for point in frontier.points
        if not point.is_optimal
    }
    assert dominated.keys() == {5}
    assert dominated[5] in {2, 3, 4}

    assert frontier.x_axis == "cost"
    assert frontier.y_axis == "quality"


def test_compute_pareto_frontier_with_single_optimal() -> None:
    results = [
        _make_result(1, quality=0.92, cost=0.003, latency=150.0),
        _make_result(2, quality=0.80, cost=0.004, latency=210.0),
        _make_result(3, quality=0.78, cost=0.006, latency=240.0),
    ]

    frontier = ParetoFrontier.compute(results, experiment_id="run-456")

    assert [point.test_number for point in frontier.optimal_points] == [1]
    dominated = {point.test_number: point.dominated_by for point in frontier.points if not point.is_optimal}
    assert dominated == {2: 1, 3: 1}


def test_budget_helpers_identify_candidates() -> None:
    results = [
        _make_result(1, quality=0.70, cost=0.002, latency=120.0),
        _make_result(2, quality=0.85, cost=0.004, latency=160.0),
        _make_result(3, quality=0.83, cost=0.003, latency=140.0),
        _make_result(4, quality=0.90, cost=0.006, latency=220.0),
    ]
    frontier = ParetoFrontier.compute(results, experiment_id="run-budget")

    within = frontier.points_within_budget(0.0045)
    assert [point.test_number for point in within] == [1, 2, 3]

    best = frontier.best_within_budget(0.0045)
    assert best is not None
    assert best.test_number == 2

    with pytest.raises(ValueError):
        frontier.points_within_budget(-0.1)


def test_visualize_generates_image(tmp_path: Path) -> None:
    results = [
        _make_result(1, quality=0.70, cost=0.002, latency=120.0),
        _make_result(2, quality=0.85, cost=0.004, latency=160.0),
        _make_result(3, quality=0.83, cost=0.003, latency=140.0),
        _make_result(4, quality=0.90, cost=0.006, latency=220.0),
    ]
    frontier = ParetoFrontier.compute(results, experiment_id="run-visual")

    output_path = tmp_path / "pareto.png"
    image_path = frontier.visualize(output_path, budget_threshold=0.0045)

    assert image_path == output_path
    assert output_path.exists()


def test_compute_with_latency_axis() -> None:
    results = [
        _make_result(1, quality=0.88, cost=0.004, latency=300.0),
        _make_result(2, quality=0.86, cost=0.003, latency=220.0),
        _make_result(3, quality=0.92, cost=0.006, latency=250.0),
    ]

    frontier = ParetoFrontier.compute(
        results,
        experiment_id="run-latency",
        x_axis="latency",
    )

    assert frontier.x_axis == "latency"
    assert {point.test_number for point in frontier.optimal_points} == {2, 3}
