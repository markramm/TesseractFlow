import pytest
import yaml

from tesseract_flow.core.config import ExperimentConfig, ExperimentRun, TestResult, UtilityWeights, Variable
from tesseract_flow.evaluation.metrics import DimensionScore, QualityScore
from tesseract_flow.experiments.analysis import (
    MainEffectsAnalyzer,
    calculate_quality_improvement,
    compare_configurations,
    export_optimal_config,
    identify_optimal_config,
)
from tesseract_flow.experiments.taguchi import generate_test_configs


def _quality_score(value: float) -> QualityScore:
    return QualityScore(
        dimension_scores={"clarity": DimensionScore(score=value, reasoning="solid")},
        evaluator_model="stub",
    )


def test_main_effects_analysis_and_exports(tmp_path) -> None:
    variables = [
        Variable(name="temperature", level_1=0.2, level_2=0.8),
        Variable(name="model", level_1="gpt-4", level_2="claude"),
        Variable(name="context", level_1="file", level_2="module"),
        Variable(name="strategy", level_1="standard", level_2="cot"),
    ]
    config = ExperimentConfig(
        name="analysis-test",
        workflow="code_review",
        variables=variables,
        utility_weights=UtilityWeights(quality=1.0, cost=0.0, time=0.0),
    )
    test_configs = generate_test_configs(config)
    run = ExperimentRun(
        experiment_id="analysis-run",
        config=config,
        test_configurations=test_configs,
    ).mark_running()

    quality_values = {
        1: 0.55,
        2: 0.60,
        3: 0.65,
        4: 0.62,
        5: 0.78,
        6: 0.80,
        7: 0.88,
        8: 0.90,
    }

    for test_config in test_configs:
        quality = _quality_score(quality_values[test_config.test_number])
        result = TestResult(
            test_number=test_config.test_number,
            config=test_config,
            quality_score=quality,
            cost=0.01,
            latency=1000.0,
            workflow_output=f"output {test_config.test_number}",
        )
        run = run.record_result(result)

    run = run.mark_completed()

    main_effects = MainEffectsAnalyzer.compute(
        run.results, config.variables, experiment_id=run.experiment_id
    )
    assert main_effects.experiment_id == "analysis-run"
    total_contribution = sum(effect.contribution_pct for effect in main_effects.effects.values())
    assert total_contribution == pytest.approx(100.0, abs=0.5)

    temperature_effect = main_effects.effects["temperature"]
    assert temperature_effect.effect_size > 0
    assert temperature_effect.avg_level_2 > temperature_effect.avg_level_1

    recommended = identify_optimal_config(main_effects, config.variables)
    assert recommended["temperature"] == 0.8
    assert recommended["model"] in {"gpt-4", "claude"}

    optimal_result = max(run.results, key=lambda item: item.utility)
    comparison = compare_configurations(
        run.baseline_config.config_values, optimal_result.config.config_values
    )
    assert comparison["temperature"]["changed"] is True
    assert comparison["model"]["changed"] in {True, False}

    improvement = calculate_quality_improvement(
        run.baseline_quality, optimal_result.quality_score.overall_score
    )
    assert improvement == pytest.approx(run.quality_improvement_pct)

    export_path = tmp_path / "optimal.yaml"
    exported = export_optimal_config(
        recommended,
        export_path,
        experiment_name=config.name,
        workflow=config.workflow,
    )
    assert exported == export_path
    exported_payload = yaml.safe_load(export_path.read_text(encoding="utf-8"))
    assert exported_payload["experiment"] == "analysis-test"
    assert exported_payload["workflow"] == "code_review"
    assert exported_payload["configuration"]["temperature"] == 0.8
