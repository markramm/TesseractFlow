from __future__ import annotations

from collections import Counter
from itertools import combinations

import numpy as np
import pytest

from tesseract_flow.core.config import ExperimentConfig, UtilityWeights, Variable
from tesseract_flow.experiments.taguchi import L8_ARRAY, generate_l8_array, generate_test_configs


def test_l8_array_has_expected_orthogonality() -> None:
    """Every pair of columns in the L8 array should contain each combination twice."""

    for left, right in combinations(range(L8_ARRAY.shape[1]), 2):
        pairs = Counter(tuple(row) for row in np.stack((L8_ARRAY[:, left], L8_ARRAY[:, right]), axis=1))
        for combination in [(1, 1), (1, 2), (2, 1), (2, 2)]:
            assert pairs[combination] == 2


def test_generate_l8_array_validates_variable_count() -> None:
    with pytest.raises(ValueError):
        generate_l8_array(3)
    with pytest.raises(ValueError):
        generate_l8_array(8)


def test_generate_l8_array_truncates_columns() -> None:
    truncated = generate_l8_array(4)
    assert truncated.shape == (8, 4)
    assert np.array_equal(truncated, L8_ARRAY[:, :4])
    assert truncated is not L8_ARRAY


def test_generate_test_configs_matches_array() -> None:
    variables = [
        Variable(name="temperature", level_1=0.1, level_2=0.9),
        Variable(name="model", level_1="gpt-4", level_2="claude"),
        Variable(name="context", level_1="summary", level_2="full"),
        Variable(name="strategy", level_1="standard", level_2="cot"),
    ]
    config = ExperimentConfig(
        name="code_review_trial",
        workflow="code_review",
        variables=variables,
        utility_weights=UtilityWeights(),
    )

    test_configs = generate_test_configs(config)
    assert len(test_configs) == 8

    variable_levels = {
        variable.name: {variable.level_1: 1, variable.level_2: 2} for variable in variables
    }
    variable_indices = {variable.name: position for position, variable in enumerate(variables)}

    for index, (row, test_config) in enumerate(
        zip(generate_l8_array(len(variables)), test_configs, strict=True), start=1
    ):
        assert test_config.test_number == index
        assert set(test_config.config_values) == {variable.name for variable in variables}
        for variable in variables:
            value = test_config.config_values[variable.name]
            assert value in {variable.level_1, variable.level_2}
            assert variable_levels[variable.name][value] == row[variable_indices[variable.name]]
        assert test_config.workflow == config.workflow

