"""CLI commands for analyzing experiment results."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from tesseract_flow.core.config import ExperimentRun, TestResult, Variable
from tesseract_flow.experiments.analysis import (
    MainEffectsAnalyzer,
    calculate_quality_improvement,
    export_optimal_config,
    identify_optimal_config,
)

app = typer.Typer(help="Analyze experiment results")
console = Console()
logger = logging.getLogger(__name__)


@app.command()
def main_effects(
    results_file: Path = typer.Argument(..., help="Path to experiment results JSON file"),
    *,
    export: Optional[Path] = typer.Option(
        None,
        "--export",
        "-o",
        help="Export optimal configuration to YAML file",
    ),
    show_config: bool = typer.Option(
        True,
        "--show-config/--no-show-config",
        help="Display recommended optimal configuration",
    ),
) -> None:
    """
    Analyze main effects to identify variable contributions and optimal configuration.

    This command performs Taguchi main effects analysis on experiment results,
    showing which variables contribute most to utility (quality, cost, time trade-off).
    """
    logger.info("Loading experiment results from %s", results_file)

    # Load results
    if not results_file.exists():
        console.print(f"[red]✗[/red] Results file not found: {results_file}")
        raise typer.Exit(code=1)

    try:
        with results_file.open("r") as f:
            data = json.load(f)
        experiment_results = ExperimentRun(**data)
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to load results: {e}")
        logger.exception("Failed to parse experiment results")
        raise typer.Exit(code=1) from e

    # Validate we have 8 results
    if len(experiment_results.results) != 8:
        console.print(
            f"[yellow]⚠[/yellow] Expected 8 results for L8 analysis, got {len(experiment_results.results)}"
        )

    # Extract variables and results
    variables: list[Variable] = experiment_results.config.variables
    results: list[TestResult] = experiment_results.results

    console.print(f"[green]✓[/green] Loaded experiment: {experiment_results.experiment_id}")
    console.print(f"  • Variables tested: {len(variables)}")
    console.print(f"  • Test configurations: {len(results)}")
    console.print()

    # Compute main effects
    try:
        main_effects_result = MainEffectsAnalyzer.compute(
            results=results,
            variables=variables,
            experiment_id=experiment_results.experiment_id,
        )
    except Exception as e:
        console.print(f"[red]✗[/red] Main effects analysis failed: {e}")
        logger.exception("Main effects computation failed")
        raise typer.Exit(code=1) from e

    # Display main effects table
    console.print("[bold]Main Effects Analysis[/bold]")
    console.print("=" * 80)
    console.print()

    effects_table = Table(title="Variable Contributions to Utility")
    effects_table.add_column("Variable", style="cyan", no_wrap=True)
    effects_table.add_column("Level 1 Avg", justify="right", style="white")
    effects_table.add_column("Level 2 Avg", justify="right", style="white")
    effects_table.add_column("Effect Size", justify="right", style="yellow")
    effects_table.add_column("Contribution %", justify="right", style="green")
    effects_table.add_column("Recommendation", style="magenta")

    # Sort by contribution (highest first)
    sorted_effects = sorted(
        main_effects_result.effects.items(),
        key=lambda x: x[1].contribution_pct,
        reverse=True,
    )

    for var_name, effect in sorted_effects:
        # Determine which level is better
        if effect.avg_level_2 > effect.avg_level_1:
            recommendation = f"Level 2 (+{effect.effect_size:.3f})"
            rec_style = "green"
        elif effect.avg_level_1 > effect.avg_level_2:
            recommendation = f"Level 1 ({effect.effect_size:.3f})"
            rec_style = "green"
        else:
            recommendation = "No difference"
            rec_style = "yellow"

        effects_table.add_row(
            var_name,
            f"{effect.avg_level_1:.4f}",
            f"{effect.avg_level_2:.4f}",
            f"{effect.effect_size:+.4f}",
            f"{effect.contribution_pct:.1f}%",
            f"[{rec_style}]{recommendation}[/{rec_style}]",
        )

    console.print(effects_table)
    console.print()

    # Identify optimal configuration
    optimal_config = identify_optimal_config(main_effects_result, variables)

    if show_config:
        console.print("[bold]Optimal Configuration (Highest Utility)[/bold]")
        console.print("=" * 80)
        console.print()

        config_table = Table(show_header=True)
        config_table.add_column("Variable", style="cyan")
        config_table.add_column("Recommended Value", style="green")

        for var_name in sorted(optimal_config.keys()):
            config_table.add_row(var_name, str(optimal_config[var_name]))

        console.print(config_table)
        console.print()

    # Show quality improvement vs baseline
    if experiment_results.baseline_result and experiment_results.baseline_quality is not None:
        # Find optimal result
        optimal_result = max(results, key=lambda r: r.utility)
        optimal_quality = optimal_result.quality_score.overall_score

        improvement_pct = calculate_quality_improvement(
            experiment_results.baseline_quality,
            optimal_quality,
        )

        if improvement_pct is not None:
            console.print("[bold]Quality Improvement[/bold]")
            console.print("=" * 80)
            console.print(f"  • Baseline quality (Test #{experiment_results.baseline_test_number}): {experiment_results.baseline_quality:.3f}")
            console.print(f"  • Optimal quality (Test #{optimal_result.test_number}): {optimal_quality:.3f}")
            if improvement_pct > 0:
                console.print(f"  • [green]Improvement: +{improvement_pct:.1f}%[/green]")
            elif improvement_pct < 0:
                console.print(f"  • [red]Decline: {improvement_pct:.1f}%[/red]")
            else:
                console.print(f"  • No change")
            console.print()

    # Export optimal config if requested
    if export:
        try:
            exported_path = export_optimal_config(
                optimal_config,
                export,
                experiment_name=experiment_results.config.name,
                workflow=experiment_results.config.workflow,
            )
            console.print(f"[green]✓[/green] Exported optimal configuration to: {exported_path}")
        except Exception as e:
            console.print(f"[red]✗[/red] Failed to export configuration: {e}")
            logger.exception("Failed to export optimal config")

    console.print()
    console.print("[dim]Analysis complete. Use 'tesseract visualize pareto' to see quality/cost trade-offs.[/dim]")


@app.command()
def summary(
    results_file: Path = typer.Argument(..., help="Path to experiment results JSON file"),
) -> None:
    """
    Display a summary of experiment results.

    Shows an overview of test configurations, quality scores, costs, and latencies.
    """
    logger.info("Loading experiment results from %s", results_file)

    # Load results
    if not results_file.exists():
        console.print(f"[red]✗[/red] Results file not found: {results_file}")
        raise typer.Exit(code=1)

    try:
        with results_file.open("r") as f:
            data = json.load(f)
        experiment_results = ExperimentRun(**data)
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to load results: {e}")
        logger.exception("Failed to parse experiment results")
        raise typer.Exit(code=1) from e

    # Display summary
    console.print(f"[bold]Experiment Summary: {experiment_results.experiment_id}[/bold]")
    console.print("=" * 90)
    console.print()

    console.print(f"  • Name: {experiment_results.config.name}")
    console.print(f"  • Workflow: {experiment_results.config.workflow}")
    console.print(f"  • Variables: {len(experiment_results.config.variables)}")
    console.print(f"  • Tests completed: {len(experiment_results.results)}/8")
    console.print(f"  • Status: {experiment_results.status}")
    console.print()

    # Results table
    results_table = Table(title="Test Results")
    results_table.add_column("Test", justify="right", style="cyan")
    results_table.add_column("Quality", justify="right", style="green")
    results_table.add_column("Cost ($)", justify="right", style="yellow")
    results_table.add_column("Latency (s)", justify="right", style="blue")
    results_table.add_column("Utility", justify="right", style="magenta")

    for result in experiment_results.results:
        results_table.add_row(
            str(result.test_number),
            f"{result.quality_score.overall_score:.3f}",
            f"{result.cost:.4f}",
            f"{result.latency:.1f}",
            f"{result.utility:.4f}",
        )

    console.print(results_table)
    console.print()

    # Find best configurations
    best_quality = max(experiment_results.results, key=lambda r: r.quality_score.overall_score)
    best_utility = max(experiment_results.results, key=lambda r: r.utility)

    console.print("[bold]Best Configurations[/bold]")
    console.print(f"  • Highest quality: Test #{best_quality.test_number} (quality={best_quality.quality_score.overall_score:.3f})")
    console.print(f"  • Highest utility: Test #{best_utility.test_number} (utility={best_utility.utility:.4f})")
    console.print()

    console.print("[dim]Run 'tesseract analyze main-effects' for detailed variable analysis.[/dim]")


__all__ = ["app"]
