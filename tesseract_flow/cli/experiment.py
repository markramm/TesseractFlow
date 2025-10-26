"""Experiment-related CLI commands for TesseractFlow."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Union

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from tesseract_flow.core.config import ExperimentConfig, ExperimentRun, TestConfiguration
from tesseract_flow.core.exceptions import (
    CacheError,
    ConfigurationError,
    EvaluationError,
    ExperimentError,
)
from tesseract_flow.evaluation.cache import FileCacheBackend
from tesseract_flow.evaluation.rubric import RubricEvaluator
from tesseract_flow.experiments.analysis import (
    MainEffects,
    MainEffectsAnalyzer,
    calculate_quality_improvement,
    compare_configurations,
    export_optimal_config,
    identify_optimal_config,
)
from tesseract_flow.experiments.executor import ExperimentExecutor
from tesseract_flow.experiments.taguchi import generate_test_configs
from tesseract_flow.workflows.code_review import CodeReviewWorkflow

console = Console()
app = typer.Typer()
logger = logging.getLogger(__name__)

_CONFIG_ERROR_EXIT = 1
_EXECUTION_ERROR_EXIT = 2
_IO_ERROR_EXIT = 3


@app.command("run")
def run_experiment(
    ctx: typer.Context,
    config_file: Path = typer.Argument(..., exists=True, readable=True, help="Experiment YAML file."),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Destination JSON file for experiment results.",
        dir_okay=False,
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate configuration without executing."),
    resume: bool = typer.Option(False, "--resume", help="Resume an interrupted experiment from output file."),
    use_cache: bool = typer.Option(False, "--use-cache", help="Replay cached evaluator responses."),
    record_cache: bool = typer.Option(False, "--record-cache", help="Store evaluator responses to cache."),
    cache_dir: Optional[Path] = typer.Option(
        None,
        "--cache-dir",
        help="Directory for evaluator cache files (defaults to ~/.cache/tesseract_flow/evaluations).",
        file_okay=False,
    ),
    extra_instructions: Optional[str] = typer.Option(
        None,
        "--instructions",
        help="Additional rubric guidance appended to evaluator prompt.",
    ),
) -> None:
    """Execute the Taguchi experiment defined in *config_file*."""

    configure_logging(verbose, log_level=_ctx_log_level(ctx))

    try:
        config = ExperimentConfig.from_yaml(config_file)
    except (OSError, FileNotFoundError) as exc:
        console.print(f"[bold red]✗ Error:[/] Failed to read configuration: {exc}")
        raise typer.Exit(code=_IO_ERROR_EXIT) from exc
    except ConfigurationError as exc:
        _render_configuration_error(exc)
        raise typer.Exit(code=_CONFIG_ERROR_EXIT) from exc
    except (ValidationError, ValueError) as exc:
        _render_configuration_error(ConfigurationError(str(exc)))
        raise typer.Exit(code=_CONFIG_ERROR_EXIT) from exc

    console.print(f"[green]✓ Loaded experiment config:[/] {config.name}")

    if dry_run:
        _handle_dry_run(config)
        raise typer.Exit(code=0)

    if resume and output is None:
        console.print("[bold red]✗ Error:[/] --resume requires --output pointing to saved results.")
        raise typer.Exit(code=_IO_ERROR_EXIT)

    resolved_output = output or _default_output_path(config.name)
    resolved_output = resolved_output.resolve()
    console.print(f"[cyan]• Results will be written to:[/] {resolved_output}")

    resume_run: Optional[ExperimentRun] = None
    if resume:
        try:
            resume_run = load_run(resolved_output)
        except (OSError, ValueError, ValidationError) as exc:
            console.print(f"[bold red]✗ Error:[/] Unable to load saved results: {exc}")
            raise typer.Exit(code=_IO_ERROR_EXIT) from exc
        console.print(
            f"[yellow]↻ Resuming run:[/] {resume_run.experiment_id} (completed {len(resume_run.results)}/"
            f"{len(resume_run.test_configurations)} tests)"
        )

    try:
        evaluator_model = None
        if config.workflow_config:
            evaluator_model = config.workflow_config.evaluator_model
        evaluator = build_evaluator(
            use_cache=use_cache,
            record_cache=record_cache,
            cache_dir=cache_dir,
            evaluator_model=evaluator_model,
        )
    except (CacheError, ValueError) as exc:
        console.print(f"[bold red]✗ Error:[/] Failed to initialize evaluator: {exc}")
        raise typer.Exit(code=_CONFIG_ERROR_EXIT) from exc

    executor = build_executor(config, evaluator)

    try:
        run = asyncio.run(
            _execute_experiment(
                executor,
                config,
                output_path=resolved_output,
                resume_from=resume_run,
                extra_instructions=extra_instructions,
            )
        )
    except (EvaluationError, ExperimentError) as exc:
        _render_execution_error(exc, resolved_output)
        raise typer.Exit(code=_EXECUTION_ERROR_EXIT) from exc
    except CacheError as exc:
        _render_cache_error(exc)
        raise typer.Exit(code=_IO_ERROR_EXIT) from exc
    except OSError as exc:
        console.print(f"[bold red]✗ Error:[/] Failed to persist results: {exc}")
        _render_recovery_tips([
            "Verify the output directory is writable.",
            "Provide an alternate path with --output.",
        ])
        raise typer.Exit(code=_IO_ERROR_EXIT) from exc

    console.print("[green]✓ All tests completed successfully")
    console.print(f"[green]✓ Results saved to:[/] {resolved_output}")
    _render_summary(run, resolved_output)


@app.command("analyze")
def analyze_results(
    ctx: typer.Context,
    results_file: Path = typer.Argument(
        ..., exists=True, readable=True, help="Experiment results JSON file."
    ),
    output_format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: table, json, or markdown.",
    ),
    export: Optional[Path] = typer.Option(
        None,
        "--export",
        "-e",
        help="Destination YAML file for recommended configuration.",
        dir_okay=False,
    ),
) -> None:
    """Analyze experiment results and display main effects."""

    configure_logging(False, log_level=_ctx_log_level(ctx))

    fmt = output_format.strip().lower()
    if fmt not in {"table", "json", "markdown"}:
        console.print("[bold red]✗ Error:[/] --format must be table, json, or markdown.")
        raise typer.Exit(code=_CONFIG_ERROR_EXIT)

    try:
        run = load_run(results_file)
    except (OSError, ValueError, ValidationError) as exc:
        console.print(f"[bold red]✗ Error:[/] Failed to load results: {exc}")
        _render_recovery_tips([
            "Ensure the file is a valid experiment JSON output.",
            "Re-run the experiment with --output to regenerate results.",
        ])
        raise typer.Exit(code=_IO_ERROR_EXIT) from exc

    if len(run.results) != 8:
        console.print("[bold red]✗ Error:[/] Completed results with 8 tests are required for analysis.")
        raise typer.Exit(code=_CONFIG_ERROR_EXIT)

    try:
        main_effects = MainEffectsAnalyzer.compute(
            run.results, run.config.variables, experiment_id=run.experiment_id
        )
    except ValueError as exc:
        console.print(f"[bold red]✗ Error:[/] {exc}")
        _render_recovery_tips([
            "Confirm the results file was produced by the current version of TesseractFlow.",
            "Re-run analysis after regenerating results.",
        ])
        raise typer.Exit(code=_CONFIG_ERROR_EXIT) from exc

    recommended_config = identify_optimal_config(main_effects, run.config.variables)
    baseline_config = run.baseline_config or run.test_configurations[0]
    baseline_result = run.baseline_result or next(
        (item for item in run.results if item.test_number == baseline_config.test_number),
        None,
    )
    baseline_quality = run.baseline_quality
    if baseline_quality is None and baseline_result is not None:
        baseline_quality = baseline_result.quality_score.overall_score

    optimal_result = max(run.results, key=lambda item: item.utility)
    improvement = run.quality_improvement_pct
    if improvement is None:
        improvement = calculate_quality_improvement(
            baseline_quality, optimal_result.quality_score.overall_score
        )

    comparison = compare_configurations(
        baseline_config.config_values, optimal_result.config.config_values
    )

    payload = _build_analysis_payload(
        run,
        main_effects,
        baseline_config.config_values,
        baseline_result,
        baseline_quality,
        optimal_result,
        recommended_config,
        improvement,
        comparison,
    )

    if fmt == "json":
        console.print_json(json.dumps(payload, default=str))
    elif fmt == "markdown":
        console.print(_render_markdown(payload))
    else:
        _render_main_effects_table(main_effects)
        _render_comparison_table(comparison)
        _render_metrics_summary(baseline_result, baseline_quality, optimal_result, improvement)
        if recommended_config != optimal_result.config.config_values:
            console.print(
                "[cyan]• Recommended configuration (main effects):[/] "
                f"{recommended_config}"
            )

    if export is not None:
        try:
            destination = export_optimal_config(
                recommended_config,
                export,
                experiment_name=run.config.name,
                workflow=run.config.workflow,
            )
        except OSError as exc:
            console.print(f"[bold red]✗ Error:[/] Failed to export configuration: {exc}")
            _render_recovery_tips([
                "Check the destination directory permissions.",
                "Choose a different file path with --export.",
            ])
            raise typer.Exit(code=_IO_ERROR_EXIT) from exc
        console.print(f"[green]✓ Exported optimal configuration to:[/] {destination}")


@app.command("status")
def status_experiment(
    ctx: typer.Context,
    results_file: Path = typer.Argument(
        ..., exists=True, readable=True, help="Experiment results JSON file."
    ),
    details: bool = typer.Option(
        False,
        "--details",
        help="Display per-test metrics for recorded results.",
    ),
) -> None:
    """Display the current status of an experiment run."""

    configure_logging(False, log_level=_ctx_log_level(ctx))

    try:
        run = load_run(results_file)
    except (OSError, ValueError, ValidationError) as exc:
        console.print(f"[bold red]✗ Error:[/] Failed to load results: {exc}")
        _render_recovery_tips([
            "Ensure the file is a valid experiment JSON output.",
            "Re-run the experiment with --output to regenerate results.",
        ])
        raise typer.Exit(code=_IO_ERROR_EXIT) from exc

    console.print(
        f"[cyan]📂 Experiment:[/] {run.config.name} [dim]({run.experiment_id})[/]"
    )
    console.print(_format_status_line(run.status))
    console.print(_build_status_table(run))

    pending = _pending_tests(run)
    if pending:
        console.print(
            "[yellow]⏳ Pending tests:[/] " + ", ".join(f"#{number}" for number in pending)
        )
    elif run.status != "COMPLETED":
        console.print("[yellow]⏳ Pending tests:[/] none (waiting for completion)")

    if run.error:
        console.print(f"[bold red]⚠️ Last error:[/] {run.error}")

    if run.results:
        latest = run.results[-1]
        console.print(
            "[green]🧪 Last recorded result:[/] "
            f"#{latest.test_number} quality={latest.quality_score.overall_score:.3f} "
            f"cost={latest.cost:.4f} latency={latest.latency:.1f}ms utility={latest.utility:.3f}"
        )
        if not details and len(run.results) < len(run.test_configurations):
            console.print(
                "[cyan]• Use --details to list all recorded metrics so far."
            )

    if details and run.results:
        console.print(_build_results_table(run.results))

    if run.status != "COMPLETED":
        console.print(
            "[cyan]Next steps:[/] Resume with "
            f"tesseract experiment run <config.yaml> --resume --output {results_file}"
        )
    else:
        console.print(
            "[green]✓ Experiment completed. Analyze with:[/] "
            f"tesseract experiment analyze {results_file}"
        )


@app.command("validate")
def validate_config(
    ctx: typer.Context,
    config_file: Path = typer.Argument(
        ..., exists=True, readable=True, help="Experiment YAML file to validate."
    ),
    show_tests: bool = typer.Option(
        False,
        "--show-tests/--hide-tests",
        help="Preview generated Taguchi test configurations.",
    ),
) -> None:
    """Validate an experiment configuration without running it."""

    configure_logging(False, log_level=_ctx_log_level(ctx))

    try:
        config = ExperimentConfig.from_yaml(config_file)
    except (OSError, FileNotFoundError) as exc:
        console.print(f"[bold red]✗ Error:[/] Failed to read configuration: {exc}")
        raise typer.Exit(code=_IO_ERROR_EXIT) from exc
    except ConfigurationError as exc:
        _render_configuration_error(exc)
        raise typer.Exit(code=_CONFIG_ERROR_EXIT) from exc
    except (ValidationError, ValueError) as exc:
        _render_configuration_error(ConfigurationError(str(exc)))
        raise typer.Exit(code=_CONFIG_ERROR_EXIT) from exc

    console.print(f"[green]✅ Configuration is valid:[/] {config.name}")
    console.print(f"[cyan]• Workflow:[/] {config.workflow}")

    variables = ", ".join(variable.name for variable in config.variables)
    console.print(f"[cyan]• Variables:[/] {variables}")

    sample_code = getattr(config.workflow_config, "sample_code_path", None)
    if sample_code:
        console.print(f"[cyan]• Sample code:[/] {sample_code}")

    rubric = getattr(config.workflow_config, "rubric", {}) or {}
    console.print(f"[cyan]• Rubric dimensions:[/] {len(rubric)}")

    if show_tests:
        _handle_dry_run(config)
    else:
        console.print(
            "[cyan]• Use --show-tests to preview the generated Taguchi configurations."
        )


def configure_logging(
    verbose: bool = False,
    *,
    log_level: Optional[Union[str, int]] = None,
) -> None:
    """Configure root logging for CLI execution."""

    resolved_level: int
    if isinstance(log_level, int):
        resolved_level = log_level
    elif isinstance(log_level, str):
        normalized = log_level.upper()
        resolved_level = getattr(logging, normalized, logging.INFO)
    else:
        resolved_level = logging.INFO

    if verbose:
        resolved_level = logging.DEBUG

    logging.basicConfig(
        level=resolved_level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
        force=True,
    )
    logging.getLogger("litellm").setLevel(logging.WARNING)
    if verbose:
        console.print("[blue]Verbose logging enabled[/]")


def _ctx_log_level(ctx: Optional[typer.Context]) -> Optional[Union[str, int]]:
    if ctx is None:
        return None
    obj = ctx.find_object(dict)
    if not obj:
        return None
    return obj.get("log_level")


def _default_output_path(config_name: str) -> Path:
    safe_name = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in config_name.strip())
    safe_name = safe_name or "experiment"
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return Path(f"results_{safe_name}_{timestamp}.json")


def build_evaluator(
    *, use_cache: bool, record_cache: bool, cache_dir: Optional[Path], evaluator_model: Optional[str] = None
) -> RubricEvaluator:
    """Return a RubricEvaluator configured with optional caching."""

    cache_backend = None
    if use_cache or record_cache:
        cache_path = (cache_dir or _default_cache_dir()).expanduser()
        cache_backend = FileCacheBackend(cache_path)
        console.print(f"[cyan]• Using evaluator cache at:[/] {cache_backend.cache_dir}")

    # Use provided evaluator_model or fall back to default
    kwargs = {"cache": cache_backend, "use_cache": use_cache, "record_cache": record_cache}
    if evaluator_model:
        kwargs["model"] = evaluator_model

    return RubricEvaluator(**kwargs)


def _default_cache_dir() -> Path:
    home = Path.home()
    return home / ".cache" / "tesseract_flow" / "evaluations"


def build_executor(config: ExperimentConfig, evaluator: RubricEvaluator) -> ExperimentExecutor:
    """Construct an ExperimentExecutor for the provided configuration."""

    def resolver(workflow_name: str, experiment_config: ExperimentConfig) -> CodeReviewWorkflow:
        normalized = workflow_name.strip().lower()
        if normalized == "code_review":
            workflow_config = experiment_config.workflow_config
            return CodeReviewWorkflow(config=workflow_config)
        msg = f"Unsupported workflow '{workflow_name}'."
        raise ExperimentError(msg)

    return ExperimentExecutor(resolver, evaluator)


def load_run(path: Path) -> ExperimentRun:
    """Load a persisted ExperimentRun from disk."""

    return ExperimentExecutor.load_run(path)


async def _execute_experiment(
    executor: ExperimentExecutor,
    config: ExperimentConfig,
    *,
    output_path: Path,
    resume_from: Optional[ExperimentRun],
    extra_instructions: Optional[str],
) -> ExperimentRun:
    """Execute an experiment with progress reporting."""

    logger.info("Executing experiment '%s' via CLI", config.name)
    total_tests = _determine_total_tests(config, resume_from)
    progress = _progress_renderer()
    task_id = progress.add_task("Running experiment", total=total_tests)

    if resume_from is not None:
        progress.update(task_id, completed=len(resume_from.results))

    def _on_progress(completed: int, total: int) -> None:
        progress.update(task_id, completed=completed, total=total)

    with progress:
        run = await executor.run(
            config,
            resume_from=resume_from,
            progress_callback=_on_progress,
            persist_path=output_path,
            extra_instructions=extra_instructions,
        )

    logger.info(
        "Experiment '%s' completed with status %s after %s results",
        config.name,
        run.status,
        len(run.results),
    )
    return run


def _determine_total_tests(config: ExperimentConfig, resume_from: Optional[ExperimentRun]) -> int:
    if resume_from is not None:
        return len(resume_from.test_configurations)
    test_configs = generate_test_configs(config)
    return len(test_configs)


def _progress_renderer() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
    )


def _handle_dry_run(config: ExperimentConfig) -> None:
    console.print("[cyan]• Generating Taguchi L8 test configurations...[/]")
    test_configs = generate_test_configs(config)
    console.print(f"[green]✓ Generated {len(test_configs)} test configurations")
    _render_test_configuration_table(config, test_configs)


def _render_test_configuration_table(
    config: ExperimentConfig, test_configs: Iterable[TestConfiguration]
) -> None:
    variable_names = [variable.name for variable in config.variables]
    table = Table(title="Test Configurations")
    table.add_column("Test #", justify="right")
    for name in variable_names:
        table.add_column(name)

    for test_config in test_configs:
        row = [str(test_config.test_number)]
        for name in variable_names:
            value = test_config.config_values.get(name)
            row.append(str(value))
        table.add_row(*row)

    console.print(table)


def _render_summary(run: ExperimentRun, output_path: Path) -> None:
    results = run.results
    if not results:
        console.print("[yellow]No results recorded for this run.[/]")
        return

    utilities = [result.utility for result in results]
    qualities = [result.quality_score.overall_score for result in results]
    costs = [result.cost for result in results]
    latencies = [result.latency for result in results]

    best_result = max(results, key=lambda result: result.utility)

    table = Table(title="Experiment Summary")
    table.add_column("Metric")
    table.add_column("Value", justify="right")

    table.add_row("Tests completed", f"{len(results)}/{len(run.test_configurations)}")
    table.add_row("Utility range", f"{min(utilities):.2f} – {max(utilities):.2f}")
    table.add_row("Quality range", f"{min(qualities):.2f} – {max(qualities):.2f}")
    table.add_row("Cost range", f"{min(costs):.4f} – {max(costs):.4f}")
    table.add_row("Latency range (ms)", f"{min(latencies):.1f} – {max(latencies):.1f}")
    table.add_row(
        "Best test",
        f"#{best_result.test_number} utility={best_result.utility:.2f}",
    )

    console.print(table)
    console.print(
        f"[cyan]Next steps:[/] tesseract analyze {output_path}"
    )


def _format_status_line(status: str) -> str:
    mapping = {
        "PENDING": ("🕒", "yellow"),
        "RUNNING": ("🚀", "cyan"),
        "COMPLETED": ("✅", "green"),
        "FAILED": ("⚠️", "red"),
    }
    icon, style = mapping.get(status.upper(), ("❔", "magenta"))
    friendly = status.replace("_", " ").title()
    return f"[{style}]{icon}[/] [bold {style}]{friendly}[/]"


def _build_status_table(run: ExperimentRun) -> Table:
    table = Table(title="Progress Overview")
    table.add_column("Metric")
    table.add_column("Value", justify="right")

    total = len(run.test_configurations)
    completed = len(run.results)
    table.add_row("Completed tests", f"{completed}/{total}")
    table.add_row("Started", _format_timestamp(run.started_at))
    table.add_row("Completed", _format_timestamp(run.completed_at))

    if run.results:
        table.add_row("Last update", _format_timestamp(run.results[-1].timestamp))

    if run.started_at:
        if run.completed_at:
            table.add_row(
                "Duration",
                _format_duration(run.completed_at - run.started_at),
            )
        elif run.status == "RUNNING":
            elapsed = datetime.now(tz=run.started_at.tzinfo) - run.started_at
            table.add_row("Elapsed", _format_duration(elapsed))

    if run.baseline_quality is not None:
        table.add_row("Baseline quality", f"{run.baseline_quality:.3f}")
    if run.quality_improvement_pct is not None:
        table.add_row("Quality improvement", f"{run.quality_improvement_pct:.2f}%")

    if run.results:
        utilities = [result.utility for result in run.results]
        qualities = [result.quality_score.overall_score for result in run.results]
        table.add_row(
            "Utility range",
            f"{min(utilities):.3f} – {max(utilities):.3f}",
        )
        table.add_row(
            "Quality range",
            f"{min(qualities):.3f} – {max(qualities):.3f}",
        )

    return table


def _build_results_table(results: Sequence[TestResult]) -> Table:
    table = Table(title="Recorded Results")
    table.add_column("Test #", justify="right")
    table.add_column("Quality", justify="right")
    table.add_column("Cost (USD)", justify="right")
    table.add_column("Latency (ms)", justify="right")
    table.add_column("Utility", justify="right")
    table.add_column("Timestamp")

    for result in sorted(results, key=lambda item: item.test_number):
        table.add_row(
            str(result.test_number),
            f"{result.quality_score.overall_score:.3f}",
            f"{result.cost:.4f}",
            f"{result.latency:.1f}",
            f"{result.utility:.3f}",
            _format_timestamp(result.timestamp),
        )

    return table


def _pending_tests(run: ExperimentRun) -> List[int]:
    completed_numbers = {result.test_number for result in run.results}
    return [
        config.test_number
        for config in sorted(run.test_configurations, key=lambda item: item.test_number)
        if config.test_number not in completed_numbers
    ]


def _format_timestamp(value: Optional[datetime]) -> str:
    if value is None:
        return "—"
    if value.tzinfo is not None:
        localized = value.astimezone()
        return localized.strftime("%Y-%m-%d %H:%M:%S %Z")
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _format_duration(delta: timedelta) -> str:
    total_seconds = int(delta.total_seconds())
    if total_seconds < 0:
        total_seconds = 0
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)


def _build_analysis_payload(
    run: ExperimentRun,
    main_effects: MainEffects,
    baseline_config: Mapping[str, object],
    baseline_result: Optional[TestResult],
    baseline_quality: Optional[float],
    optimal_result: TestResult,
    recommended_config: Mapping[str, object],
    improvement: Optional[float],
    comparison: Mapping[str, Mapping[str, object]],
) -> Dict[str, Any]:
    return {
        "experiment_id": run.experiment_id,
        "experiment_name": run.config.name,
        "main_effects": [
            {
                "variable": name,
                "avg_level_1": effect.avg_level_1,
                "avg_level_2": effect.avg_level_2,
                "effect_size": effect.effect_size,
                "sum_of_squares": effect.sum_of_squares,
                "contribution_pct": effect.contribution_pct,
            }
            for name, effect in main_effects.effects.items()
        ],
        "baseline": {
            "test_number": baseline_result.test_number if baseline_result else None,
            "config": dict(baseline_config),
            "quality": baseline_quality,
            "cost": baseline_result.cost if baseline_result else None,
            "latency": baseline_result.latency if baseline_result else None,
            "utility": baseline_result.utility if baseline_result else None,
        },
        "optimal_observed": {
            "test_number": optimal_result.test_number,
            "config": dict(optimal_result.config.config_values),
            "quality": optimal_result.quality_score.overall_score,
            "cost": optimal_result.cost,
            "latency": optimal_result.latency,
            "utility": optimal_result.utility,
        },
        "recommended_configuration": dict(recommended_config),
        "quality_improvement_pct": improvement,
        "comparison": {key: dict(value) for key, value in comparison.items()},
    }


def _render_main_effects_table(main_effects: MainEffects) -> None:
    table = Table(title="Main Effects")
    table.add_column("Variable")
    table.add_column("Avg Level 1", justify="right")
    table.add_column("Avg Level 2", justify="right")
    table.add_column("Effect", justify="right")
    table.add_column("Contribution %", justify="right")

    for name, effect in main_effects.effects.items():
        table.add_row(
            name,
            f"{effect.avg_level_1:.3f}",
            f"{effect.avg_level_2:.3f}",
            f"{effect.effect_size:.3f}",
            f"{effect.contribution_pct:.1f}",
        )

    console.print(table)


def _render_comparison_table(comparison: Mapping[str, Mapping[str, object]]) -> None:
    table = Table(title="Configuration Comparison")
    table.add_column("Variable")
    table.add_column("Baseline")
    table.add_column("Optimal")
    table.add_column("Changed", justify="center")

    for name, values in comparison.items():
        baseline_value = values.get("baseline")
        candidate_value = values.get("candidate")
        changed = values.get("changed")
        table.add_row(
            name,
            str(baseline_value),
            str(candidate_value),
            "✅" if changed else "—",
        )

    console.print(table)


def _render_metrics_summary(
    baseline_result: Optional[TestResult],
    baseline_quality: Optional[float],
    optimal_result: TestResult,
    improvement: Optional[float],
) -> None:
    table = Table(title="Baseline vs Optimal Metrics")
    table.add_column("Metric")
    table.add_column("Baseline", justify="right")
    table.add_column("Optimal", justify="right")

    table.add_row(
        "Quality",
        _format_metric(baseline_quality),
        f"{optimal_result.quality_score.overall_score:.3f}",
    )
    table.add_row(
        "Cost (USD)",
        _format_metric(baseline_result.cost if baseline_result else None, precision=4),
        f"{optimal_result.cost:.4f}",
    )
    table.add_row(
        "Latency (ms)",
        _format_metric(baseline_result.latency if baseline_result else None, precision=1),
        f"{optimal_result.latency:.1f}",
    )
    table.add_row(
        "Utility",
        _format_metric(baseline_result.utility if baseline_result else None),
        f"{optimal_result.utility:.3f}",
    )

    console.print(table)

    if improvement is None:
        console.print("[yellow]Quality improvement could not be calculated.[/]")
        return

    if improvement < 0:
        color = "red"
    elif 10.0 <= improvement <= 30.0:
        color = "green"
    else:
        color = "yellow"
    console.print(f"[{color}]Quality improvement: {improvement:.2f}%[/]")


def _render_markdown(payload: Mapping[str, Any]) -> str:
    lines = [
        f"# Experiment Analysis: {payload['experiment_id']}",
        "",
        "## Main Effects",
        "| Variable | Avg Level 1 | Avg Level 2 | Effect | Contribution % |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for effect in payload["main_effects"]:
        lines.append(
            "| {variable} | {avg_level_1:.3f} | {avg_level_2:.3f} | {effect_size:.3f} | {contribution_pct:.1f} |".format(
                **effect
            )
        )

    lines.extend(
        [
            "",
            "## Baseline vs Optimal",
            "| Metric | Baseline | Optimal |",
            "| --- | ---: | ---: |",
        ]
    )

    baseline = payload["baseline"]
    optimal = payload["optimal_observed"]
    lines.append(
        f"| Quality | {_format_markdown_value(baseline['quality'])} | {optimal['quality']:.3f} |"
    )
    lines.append(
        f"| Cost (USD) | {_format_markdown_value(baseline['cost'], precision=4)} | {optimal['cost']:.4f} |"
    )
    lines.append(
        f"| Latency (ms) | {_format_markdown_value(baseline['latency'], precision=1)} | {optimal['latency']:.1f} |"
    )
    lines.append(
        f"| Utility | {_format_markdown_value(baseline['utility'])} | {optimal['utility']:.3f} |"
    )

    lines.extend(
        [
            "",
            "### Configuration Changes",
            "| Variable | Baseline | Optimal | Changed |",
            "| --- | --- | --- | --- |",
        ]
    )

    for name, values in payload["comparison"].items():
        changed = "Yes" if values.get("changed") else "No"
        lines.append(
            f"| {name} | {values.get('baseline')} | {values.get('candidate')} | {changed} |"
        )

    improvement = payload.get("quality_improvement_pct")
    lines.append("")
    if improvement is not None:
        lines.append(f"Quality improvement: {improvement:.2f}%")
    else:
        lines.append("Quality improvement: N/A")

    lines.extend(
        [
            "",
            "### Recommended Configuration",
            "```json",
            json.dumps(payload["recommended_configuration"], indent=2),
            "```",
        ]
    )

    return "\n".join(lines)


def _format_metric(value: Optional[float], *, precision: int = 3) -> str:
    if value is None:
        return "N/A"
    return f"{value:.{precision}f}"


def _format_markdown_value(value: Optional[float], *, precision: int = 3) -> str:
    if value is None:
        return "N/A"
    return f"{value:.{precision}f}"


def _render_configuration_error(exc: ConfigurationError) -> None:
    console.print("[bold red]✗ Error:[/] Invalid experiment configuration.")
    if getattr(exc, "details", None):
        for detail in exc.details:
            console.print(f"  [red]-[/] {detail}")
    else:
        console.print(f"  [red]-[/] {exc}")
    _render_recovery_tips(
        [
            "Run with --dry-run to validate fixes without executing the workflow.",
            "Cross-check variable names and workflow configuration against the specification.",
        ]
    )


def _render_execution_error(exc: Exception, output_path: Path) -> None:
    console.print(f"[bold red]✗ Experiment execution failed:[/] {exc}")
    tips = [
        "Inspect the saved results file for partial progress.",
        "Resume the run with --resume once issues are resolved.",
    ]
    if output_path.exists():
        console.print(f"[yellow]! Partial results available at:[/] {output_path}")
    else:
        tips.append("Ensure the output directory exists and is writable.")
    _render_recovery_tips(tips)


def _render_cache_error(exc: CacheError) -> None:
    console.print(f"[bold red]✗ Cache error:[/] {exc}")
    _render_recovery_tips(
        [
            "Verify the cache directory path and permissions.",
            "Retry without --use-cache to bypass cached responses.",
        ]
    )


def _render_recovery_tips(tips: Sequence[str]) -> None:
    if not tips:
        return
    console.print("[yellow]Suggested next steps:[/]")
    for tip in tips:
        console.print(f"  [yellow]-[/] {tip}")


__all__ = [
    "app",
    "analyze_results",
    "build_evaluator",
    "build_executor",
    "configure_logging",
    "load_run",
    "run_experiment",
    "status_experiment",
    "validate_config",
]
