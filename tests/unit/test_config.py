from pathlib import Path

import pytest

from tesseract_flow.core.config import (
    ExperimentConfig,
    ExperimentMetadata,
    ExperimentRun,
    TestConfiguration,
    TestResult,
    UtilityWeights,
    Variable,
    WorkflowConfig,
)
from tesseract_flow.core.exceptions import ConfigurationError
from tesseract_flow.evaluation.metrics import DimensionScore, QualityScore


@pytest.fixture
def variables() -> list[Variable]:
    return [
        Variable(name="temperature", level_1=0.3, level_2=0.7),
        Variable(name="model", level_1="gpt-4", level_2="claude"),
        Variable(name="context", level_1="file", level_2="module"),
        Variable(name="strategy", level_1="standard", level_2="cot"),
    ]


@pytest.fixture
def experiment_config(variables: list[Variable]) -> ExperimentConfig:
    return ExperimentConfig(
        name="experiment",
        workflow="code_review",
        variables=variables,
    )


def _quality_score(overall: float = 0.75) -> QualityScore:
    return QualityScore(
        dimension_scores={
            "clarity": DimensionScore(score=overall, reasoning=""),
        },
        evaluator_model="gpt-4o",
    )


def _test_configurations(config: ExperimentConfig) -> list[TestConfiguration]:
    base_values = {
        variable.name: variable.level_1 for variable in config.variables
    }
    return [
        TestConfiguration(
            test_number=index + 1,
            config_values=dict(base_values),
            workflow=config.workflow,
        )
        for index in range(8)
    ]


def test_variable_valid_creation() -> None:
    variable = Variable(name="temperature", level_1=0.3, level_2=0.7)
    assert variable.level_1 == 0.3
    assert variable.level_2 == 0.7


def test_variable_rejects_identical_levels() -> None:
    with pytest.raises(ValueError):
        Variable(name="temperature", level_1=0.3, level_2=0.3)


def test_variable_rejects_mismatched_types() -> None:
    with pytest.raises(ValueError):
        Variable(name="temperature", level_1=0.3, level_2="0.7")


def test_variable_validate_name_helpers() -> None:
    with pytest.raises(ValueError):
        Variable._validate_name("")


def test_variable_rejects_invalid_names() -> None:
    with pytest.raises(ValueError):
        Variable(name=" temperature ", level_1=0.1, level_2=0.9)

    with pytest.raises(ValueError):
        Variable(name="_hidden", level_1=0.1, level_2=0.9)

    with pytest.raises(ValueError):
        Variable(name="invalid-name", level_1=0.1, level_2=0.9)


def test_utility_weights_requires_positive_weight() -> None:
    with pytest.raises(ValueError):
        UtilityWeights(quality=0.0, cost=0.0, time=0.0)


def test_workflow_config_allows_null_sample_code_path() -> None:
    config = WorkflowConfig(sample_code_path=None)
    assert config.sample_code_path is None


def test_workflow_config_rejects_blank_sample_code_path() -> None:
    with pytest.raises(ValueError):
        WorkflowConfig(sample_code_path="   ")


def test_experiment_metadata_from_config_generates_stable_hash(
    experiment_config: ExperimentConfig,
) -> None:
    metadata = ExperimentMetadata.from_config(
        experiment_config, dependencies={"pydantic": "2.0.0"}
    )
    assert metadata.config_hash
    assert metadata.seed == experiment_config.seed

    second = ExperimentMetadata.from_config(
        experiment_config, dependencies={"pydantic": "2.0.0"}
    )
    assert metadata.config_hash == second.config_hash


def test_experiment_metadata_normalizes_sources(experiment_config: ExperimentConfig) -> None:
    metadata = ExperimentMetadata.from_config(
        experiment_config,
        non_deterministic_sources=["llm_sampling", "  rate_limits  ", "llm_sampling"],
    )
    assert metadata.non_deterministic_sources == ["llm_sampling", "rate_limits"]


def test_experiment_config_validates_variable_count(variables: list[Variable]) -> None:
    config = ExperimentConfig(
        name="experiment",
        workflow="code_review",
        variables=variables,
        utility_weights=UtilityWeights(),
    )
    assert config.name == "experiment"
    assert len(config.variables) == 4


@pytest.mark.parametrize("count", [3, 8])
def test_experiment_config_rejects_invalid_variable_counts(
    count: int, variables: list[Variable]
) -> None:
    if count > len(variables):
        extra = [
            Variable(name=f"extra_{index}", level_1=index, level_2=index + 1)
            for index in range(len(variables), count)
        ]
        selected = variables + extra
    else:
        selected = variables[:count]
    with pytest.raises(ValueError):
        ExperimentConfig(
            name="experiment",
            workflow="code_review",
            variables=selected,
        )


def test_experiment_config_requires_unique_variable_names(variables: list[Variable]) -> None:
    duplicate = variables + [Variable(name="temperature", level_1=0.1, level_2=0.9)]
    with pytest.raises(ValueError):
        ExperimentConfig(
            name="experiment",
            workflow="code_review",
            variables=duplicate,
        )


def test_experiment_config_coerces_workflow_config_dict(tmp_path: Path, variables: list[Variable]) -> None:
    config = ExperimentConfig(
        name="experiment",
        workflow="code_review",
        variables=variables,
        workflow_config={
            "rubric": {
                "clarity": {
                    "description": "Clarity of review",
                    "scale": "1-5",
                }
            },
            "sample_code_path": " examples/code.py ",
            "extra_setting": True,
        },
    )
    assert isinstance(config.workflow_config, WorkflowConfig)
    assert config.workflow_config.sample_code_path == "examples/code.py"
    assert config.workflow_config.rubric["clarity"]["scale"] == "1-5"
    assert getattr(config.workflow_config, "extra_setting") is True

    output_path = tmp_path / "config.yaml"
    config.to_yaml(output_path)
    loaded = ExperimentConfig.from_yaml(output_path)
    assert loaded.name == config.name
    assert len(loaded.variables) == len(config.variables)


@pytest.mark.parametrize("field", ["name", "workflow"])
def test_experiment_config_rejects_blank_identifiers(
    field: str, variables: list[Variable]
) -> None:
    kwargs: dict[str, object] = {
        "name": "experiment",
        "workflow": "code_review",
        "variables": variables,
    }
    kwargs[field] = " test "
    with pytest.raises(ValueError):
        ExperimentConfig(**kwargs)  # type: ignore[arg-type]

    kwargs[field] = ""
    with pytest.raises(ValueError):
        ExperimentConfig(**kwargs)  # type: ignore[arg-type]


def test_experiment_config_from_yaml_requires_mapping(tmp_path: Path) -> None:
    path = tmp_path / "invalid.yaml"
    path.write_text("- item\n", encoding="utf-8")
    with pytest.raises(ConfigurationError):
        ExperimentConfig.from_yaml(path)


def test_test_configuration_without_context_skips_validation() -> None:
    config = TestConfiguration(test_number=1, config_values={"temperature": 0.1}, workflow="wf")
    assert config.config_values["temperature"] == 0.1


def test_test_configuration_requires_matching_variables() -> None:
    with pytest.raises(ValueError):
        TestConfiguration.model_validate(
            {
                "test_number": 1,
                "config_values": {"temperature": 0.1},
                "workflow": "wf",
            },
            context={
                "variable_levels": {
                    "temperature": {0.1, 0.9},
                    "model": {"gpt-4", "claude"},
                }
            },
        )


def test_test_configuration_requires_defined_levels() -> None:
    with pytest.raises(ValueError):
        TestConfiguration.model_validate(
            {
                "test_number": 1,
                "config_values": {
                    "temperature": 0.5,
                    "model": "gpt-4",
                },
                "workflow": "wf",
            },
            context={
                "variable_levels": {
                    "temperature": {0.1, 0.9},
                    "model": {"gpt-4", "claude"},
                }
            },
        )


def test_test_configuration_rejects_extra_variables() -> None:
    with pytest.raises(ValueError):
        TestConfiguration.model_validate(
            {
                "test_number": 1,
                "config_values": {"temperature": 0.1, "extra": "value"},
                "workflow": "wf",
            },
            context={"variable_levels": {"temperature": {0.1, 0.9}}},
        )


def test_test_configuration_rejects_invalid_workflow_identifier() -> None:
    with pytest.raises(ValueError):
        TestConfiguration(test_number=1, config_values={}, workflow="  invalid  ")

    with pytest.raises(ValueError):
        TestConfiguration(test_number=1, config_values={}, workflow="")


def test_test_result_trims_workflow_output(experiment_config: ExperimentConfig) -> None:
    test_config = _test_configurations(experiment_config)[0]
    score = _quality_score(0.8)
    result = TestResult(
        test_number=1,
        config=test_config,
        quality_score=score,
        cost=0.01,
        latency=1200,
        workflow_output="   Analysis complete   ",
    )
    assert result.workflow_output == "Analysis complete"


def test_experiment_run_records_result_and_updates_utility(
    experiment_config: ExperimentConfig,
) -> None:
    test_configs = _test_configurations(experiment_config)
    run = ExperimentRun(
        experiment_id="exp-1",
        config=experiment_config,
        test_configurations=test_configs,
    ).mark_running()

    score = _quality_score(0.9)
    result = TestResult(
        test_number=1,
        config=test_configs[0],
        quality_score=score,
        cost=0.015,
        latency=1500,
        workflow_output="Result",
    )

    updated = run.record_result(result)
    assert pytest.approx(updated.results[0].utility, rel=1e-6) == pytest.approx(0.9)
    assert updated.metadata["normalization"]["cost"] == {"min": 0.015, "max": 0.015}
    assert updated.metadata["normalization"]["latency"] == {"min": 1500, "max": 1500}
    assert updated.baseline_result is not None
    assert updated.baseline_result.test_number == 1
    assert updated.baseline_quality == pytest.approx(0.9)
    assert updated.quality_improvement_pct == pytest.approx(0.0)


def test_experiment_run_requires_unique_results(experiment_config: ExperimentConfig) -> None:
    test_configs = _test_configurations(experiment_config)
    run = ExperimentRun(
        experiment_id="exp-1",
        config=experiment_config,
        test_configurations=test_configs,
    ).mark_running()

    score = _quality_score(0.7)
    result = TestResult(
        test_number=1,
        config=test_configs[0],
        quality_score=score,
        cost=0.01,
        latency=1200,
        workflow_output="Result",
    )

    run = run.record_result(result)
    with pytest.raises(ValueError):
        run.record_result(result)


def test_experiment_run_completion_requires_all_results(
    experiment_config: ExperimentConfig,
) -> None:
    test_configs = _test_configurations(experiment_config)
    run = ExperimentRun(
        experiment_id="exp-1",
        config=experiment_config,
        test_configurations=test_configs,
    ).mark_running()

    with pytest.raises(ValueError):
        run.mark_completed()


def test_experiment_run_mark_failed_requires_error_message(
    experiment_config: ExperimentConfig,
) -> None:
    test_configs = _test_configurations(experiment_config)
    run = ExperimentRun(
        experiment_id="exp-1",
        config=experiment_config,
        test_configurations=test_configs,
    ).mark_running()

    with pytest.raises(ValueError):
        run.mark_failed("   ")


def test_experiment_run_can_complete_after_all_results(
    experiment_config: ExperimentConfig,
) -> None:
    test_configs = _test_configurations(experiment_config)
    run = ExperimentRun(
        experiment_id="exp-1",
        config=experiment_config,
        test_configurations=test_configs,
    ).mark_running()

    baseline_quality: float | None = None
    for index, config_item in enumerate(test_configs, start=1):
        score = _quality_score(0.6 + index * 0.03)
        result = TestResult(
            test_number=config_item.test_number,
            config=config_item,
            quality_score=score,
            cost=0.01 + index * 0.001,
            latency=1000 + index * 25,
            workflow_output=f"Result {index}",
        )
        if baseline_quality is None:
            baseline_quality = score.overall_score
        run = run.record_result(result)

    completed = run.mark_completed()
    assert completed.status == "COMPLETED"
    assert completed.completed_at is not None
    utilities = [result.utility for result in completed.results]
    assert utilities == sorted(utilities)
    assert completed.metadata["normalization"]["cost"]["min"] == pytest.approx(0.011)
    assert completed.metadata["normalization"]["latency"]["max"] == pytest.approx(1200)
    assert completed.baseline_result is not None
    assert completed.baseline_result.test_number == 1
    assert baseline_quality is not None
    assert completed.baseline_quality == pytest.approx(baseline_quality)
    assert completed.quality_improvement_pct is not None
    assert completed.quality_improvement_pct > 0
