from typer.testing import CliRunner

from tesseract_flow.cli.main import app

runner = CliRunner()


def test_root_help_includes_global_options() -> None:
    result = runner.invoke(app, ["--help"], color=False)

    assert result.exit_code == 0
    stdout = result.stdout
    assert "--log-level" in stdout
    assert "--version" in stdout


def test_experiment_help_lists_management_commands() -> None:
    result = runner.invoke(app, ["experiment", "--help"], color=False)

    assert result.exit_code == 0
    stdout = result.stdout
    assert "status" in stdout
    assert "validate" in stdout
