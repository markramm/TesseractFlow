"""Experiment design and execution utilities."""

from tesseract_flow.core.config import Variable as ExperimentVariable
from tesseract_flow.experiments.analysis import (
    Effect,
    MainEffects,
    MainEffectsAnalyzer,
    calculate_quality_improvement,
    compare_configurations,
    export_optimal_config,
    identify_optimal_config,
)
from tesseract_flow.experiments.executor import ExperimentExecutor
from tesseract_flow.experiments.taguchi import L8_ARRAY, generate_l8_array, generate_test_configs

__all__ = [
    "L8_ARRAY",
    "Effect",
    "ExperimentExecutor",
    "ExperimentVariable",
    "MainEffects",
    "MainEffectsAnalyzer",
    "calculate_quality_improvement",
    "compare_configurations",
    "export_optimal_config",
    "generate_l8_array",
    "generate_test_configs",
    "identify_optimal_config",
]
