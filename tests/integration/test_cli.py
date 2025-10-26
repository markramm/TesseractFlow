from __future__ import annotations

import json
from pathlib import Path

import yaml

from typer.testing import CliRunner

from tesseract_flow.cli.main import app
from tesseract_flow.core.config import ExperimentConfig, ExperimentRun, TestResult
from tesseract_flow.evaluation.metrics import DimensionScore, QualityScore
from tesseract_flow.experiments.taguchi import generate_test_configs

runner = CliRunner()


def _build_completed_run(config: ExperimentConfig) -> ExperimentRun:
    test_configs = generate_test_configs(config)
    run = ExperimentRun(
        experiment_id="demo-run",
        config=config,
        test_configurations=test_configs,
    ).mark_running()

    for index, test_config in enumerate(test_configs, start=1):
        quality = QualityScore(
            dimension_scores={"clarity": DimensionScore(score=min(0.5 + index * 0.05, 1.0))},
            evaluator_model="stub-model",
        )
        result = TestResult(
            test_number=test_config.test_number,
            config=test_config,
            quality_score=quality,
            cost=0.01 * index,
            latency=100.0 * index,
            workflow_output=f"output {index}",
        )
        run = run.record_result(result)

    return run.mark_completed()


def _build_running_run(config: ExperimentConfig, *, completed: int = 2) -> ExperimentRun:
    test_configs = generate_test_configs(config)
    run = ExperimentRun(
        experiment_id="demo-run",
        config=config,
        test_configurations=test_configs,
    ).mark_running()

    for index, test_config in enumerate(test_configs[:completed], start=1):
        quality = QualityScore(
            dimension_scores={"clarity": DimensionScore(score=0.6 + index * 0.05)},
            evaluator_model="stub-model",
        )
        result = TestResult(
            test_number=test_config.test_number,
            config=test_config,
            quality_score=quality,
            cost=0.02 * index,
            latency=120.0 * index,
            workflow_output=f"output {index}",
        )
        run = run.record_result(result)

    return run


def test_experiment_run_dry_run() -> None:
    config_path = Path("examples/code_review/experiment_config.yaml")

    result = runner.invoke(
        app,
        ["experiment", "run", str(config_path), "--dry-run"],
    )

    assert result.exit_code == 0
    assert "Generated 8 test configurations" in result.stdout
    assert "Test Configurations" in result.stdout


def test_experiment_run_success(monkeypatch, tmp_path) -> None:
    config_path = Path("examples/code_review/experiment_config.yaml")
    config = ExperimentConfig.from_yaml(config_path)
    completed_run = _build_completed_run(config)

    async def fake_execute(*args, **kwargs):
        output_path: Path = kwargs["output_path"]
        output_path.write_text(
            completed_run.model_dump_json(indent=2, exclude_none=True),
            encoding="utf-8",
        )
        return completed_run

    monkeypatch.setattr("tesseract_flow.cli.experiment._execute_experiment", fake_execute)

    output_path = tmp_path / "results.json"
    cache_dir = tmp_path / "cache"
    result = runner.invoke(
        app,
        [
            "experiment",
            "run",
            str(config_path),
            "--output",
            str(output_path),
            "--use-cache",
            "--record-cache",
            "--cache-dir",
            str(cache_dir),
        ],
    )

    assert result.exit_code == 0
    assert output_path.exists()
    stdout = result.stdout
    assert "All tests completed successfully" in stdout
    assert "Experiment Summary" in stdout
    assert f"tesseract analyze {output_path}" in stdout
    assert "Best test" in stdout


def test_experiment_analyze_command(tmp_path) -> None:
    config_path = Path("examples/code_review/experiment_config.yaml")
    config = ExperimentConfig.from_yaml(config_path)
    completed_run = _build_completed_run(config)

    results_path = tmp_path / "results.json"
    results_path.write_text(
        completed_run.model_dump_json(indent=2, exclude_none=True),
        encoding="utf-8",
    )

    export_path = tmp_path / "optimal.yaml"
    result = runner.invoke(
        app,
        [
            "experiment",
            "analyze",
            str(results_path),
            "--format",
            "json",
            "--export",
            str(export_path),
        ],
        color=False,
    )

    assert result.exit_code == 0
    stdout = result.stdout
    json_output, *_ = stdout.split("✓ Exported", 1)
    data = json.loads(json_output)
    assert data["experiment_id"] == "demo-run"
    assert data["baseline"]["config"]
    assert data["optimal_observed"]["config"]
    assert data["recommended_configuration"]
    assert export_path.exists()
    exported = yaml.safe_load(export_path.read_text(encoding="utf-8"))
    assert exported["workflow"] == config.workflow


def test_visualize_pareto_command(tmp_path) -> None:
    config_path = Path("examples/code_review/experiment_config.yaml")
    config = ExperimentConfig.from_yaml(config_path)
    completed_run = _build_completed_run(config)

    results_path = tmp_path / "results.json"
    results_path.write_text(
        completed_run.model_dump_json(indent=2, exclude_none=True),
        encoding="utf-8",
    )

    output_path = tmp_path / "pareto.png"
    result = runner.invoke(
        app,
        [
            "visualize",
            "pareto",
            str(results_path),
            "--output",
            str(output_path),
            "--budget",
            "0.06",
        ],
        color=False,
    )

    assert result.exit_code == 0
    assert output_path.exists()

    stdout = result.stdout
    assert "Computed Pareto frontier" in stdout
    assert "Pareto-optimal configurations" in stdout
    assert "Recommendation" in stdout


def test_experiment_status_running(tmp_path) -> None:
    config_path = Path("examples/code_review/experiment_config.yaml")
    config = ExperimentConfig.from_yaml(config_path)
    running_run = _build_running_run(config, completed=3)

    results_path = tmp_path / "partial.json"
    results_path.write_text(
        running_run.model_dump_json(indent=2, exclude_none=True),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "experiment",
            "status",
            str(results_path),
        ],
        color=False,
    )

    assert result.exit_code == 0
    stdout = result.stdout
    assert "Progress Overview" in stdout
    assert "Pending tests" in stdout
    assert "Last recorded result" in stdout
    assert "Resume with" in stdout


def test_experiment_status_completed_details(tmp_path) -> None:
    config_path = Path("examples/code_review/experiment_config.yaml")
    config = ExperimentConfig.from_yaml(config_path)
    completed_run = _build_completed_run(config)

    results_path = tmp_path / "complete.json"
    results_path.write_text(
        completed_run.model_dump_json(indent=2, exclude_none=True),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "experiment",
            "status",
            str(results_path),
            "--details",
        ],
        color=False,
    )

    assert result.exit_code == 0
    stdout = result.stdout
    assert "Recorded Results" in stdout
    assert "Experiment completed" in stdout


def test_experiment_validate_success() -> None:
    config_path = Path("examples/code_review/experiment_config.yaml")

    result = runner.invoke(
        app,
        [
            "experiment",
            "validate",
            str(config_path),
        ],
        color=False,
    )

    assert result.exit_code == 0
    stdout = result.stdout
    assert "Configuration is valid" in stdout
    assert "Use --show-tests" in stdout


def test_experiment_validate_failure(tmp_path) -> None:
    invalid_path = tmp_path / "invalid.yaml"
    invalid_path.write_text(
        "name: invalid\nworkflow: code_review\nvariables: []\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "experiment",
            "validate",
            str(invalid_path),
        ],
        color=False,
    )

    assert result.exit_code != 0
    assert "Invalid experiment configuration" in result.stdout
