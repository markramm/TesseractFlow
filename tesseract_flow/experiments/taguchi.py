"""Taguchi L8 orthogonal array utilities."""
from __future__ import annotations

from typing import Dict, Iterable, List

import numpy as np
from numpy.typing import NDArray

from tesseract_flow.core.config import ExperimentConfig, TestConfiguration, Variable

L8_ARRAY: NDArray[np.int_] = np.array(
    [
        [1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 2, 2, 2, 2],
        [1, 2, 2, 1, 1, 2, 2],
        [1, 2, 2, 2, 2, 1, 1],
        [2, 1, 2, 1, 2, 1, 2],
        [2, 1, 2, 2, 1, 2, 1],
        [2, 2, 1, 1, 2, 2, 1],
        [2, 2, 1, 2, 1, 1, 2],
    ],
    dtype=np.int_,
)
"""Standard Taguchi L8 orthogonal array supporting up to seven variables."""


def generate_l8_array(num_variables: int) -> NDArray[np.int_]:
    """Return the Taguchi L8 orthogonal array truncated to ``num_variables`` columns."""

    if num_variables < 4 or num_variables > L8_ARRAY.shape[1]:
        msg = "Taguchi L8 array requires between 4 and 7 variables."
        raise ValueError(msg)
    return np.array(L8_ARRAY[:, :num_variables], copy=True)


def _build_variable_levels(variables: Iterable[Variable]) -> Dict[str, tuple[object, object]]:
    """Map variable names to their allowed level values."""

    return {
        variable.name: (variable.level_1, variable.level_2)
        for variable in variables
    }


def generate_test_configs(config: ExperimentConfig, replications: int = 1) -> List[TestConfiguration]:
    """Generate :class:`TestConfiguration` objects for the provided experiment config.

    Args:
        config: The experiment configuration
        replications: Number of times to replicate each test configuration (default: 1)

    Returns:
        List of test configurations. If replications > 1, each unique configuration
        will appear `replications` times with sequential test numbers.
    """

    variables = config.variables
    array = generate_l8_array(len(variables))
    variable_levels = _build_variable_levels(variables)

    test_configs: List[TestConfiguration] = []
    test_number = 1

    for _ in range(replications):
        for row in array:
            config_values = {
                variable.name: (variable.level_1 if level == 1 else variable.level_2)
                for variable, level in zip(variables, row, strict=True)
            }
            test_config = TestConfiguration.model_validate(
                {
                    "test_number": test_number,
                    "workflow": config.workflow,
                    "config_values": config_values,
                },
                context={"variable_levels": variable_levels},
            )
            test_configs.append(test_config)
            test_number += 1

    return test_configs


__all__ = ["L8_ARRAY", "generate_l8_array", "generate_test_configs"]
