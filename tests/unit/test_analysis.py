import pytest

from tesseract_flow.experiments.analysis import calculate_quality_improvement


def test_quality_improvement_percentage() -> None:
    improvement = calculate_quality_improvement(0.5, 0.6)
    assert improvement == pytest.approx(20.0)


def test_quality_improvement_handles_missing_values() -> None:
    assert calculate_quality_improvement(None, 0.6) is None
    assert calculate_quality_improvement(0.5, None) is None
    assert calculate_quality_improvement(0.0, 0.6) is None
