"""Visualization-related CLI commands."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from tesseract_flow.optimization.pareto import ParetoFrontier, ParetoPoint

from .experiment import console as shared_console, load_run

app = typer.Typer()

console: Console = shared_console

_CONFIG_ERROR_EXIT = 1
_VISUALIZATION_ERROR_EXIT = 2


@app.command("pareto")
def visualize_pareto(
    results_file: Path = typer.Argument(
        ..., exists=True, readable=True, help="Experiment results JSON file."
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Destination image file (PNG, SVG, or PDF).",
    ),
    x_axis: str = typer.Option("cost", "--x-axis", help="Metric for X-axis (cost or latency)."),
    y_axis: str = typer.Option("quality", "--y-axis", help="Metric for Y-axis (quality or utility)."),
    interactive: bool = typer.Option(False, "--interactive", help="Show interactive plot window."),
    budget: Optional[float] = typer.Option(
        None,
        "--budget",
        help="Highlight configurations within the provided budget threshold.",
    ),
) -> None:
    """Generate a Pareto frontier visualization from experiment results."""

    try:
        run = load_run(results_file)
    except Exception as exc:  # noqa: BLE001 - user-facing CLI error handling
        console.print(f"[bold red]✗ Error:[/] Failed to load results: {exc}")
        raise typer.Exit(code=_CONFIG_ERROR_EXIT) from exc

    if not run.results:
        console.print("[bold red]✗ Error:[/] The results file contains no test executions.")
        raise typer.Exit(code=_CONFIG_ERROR_EXIT)

    axis_x = x_axis.strip().lower()
    axis_y = y_axis.strip().lower()

    try:
        frontier = ParetoFrontier.compute(
            run.results,
            experiment_id=run.experiment_id,
            x_axis=axis_x,
            y_axis=axis_y,
        )
    except ValueError as exc:
        console.print(f"[bold red]✗ Error:[/] {exc}")
        raise typer.Exit(code=_CONFIG_ERROR_EXIT) from exc

    console.print(f"[green]✓ Loaded {len(run.results)} test results")
    console.print(
        f"[green]✓ Computed Pareto frontier:[/] {len(frontier.optimal_points)} optimal points"
    )

    destination = output or _default_output_path(results_file, axis_x, axis_y)

    try:
        image_path = frontier.visualize(
            destination,
            show=interactive,
            budget_threshold=budget,
            title=f"Pareto Frontier for {run.config.name}",
        )
    except Exception as exc:  # noqa: BLE001 - ensure user-friendly CLI errors
        console.print(f"[bold red]✗ Error:[/] Failed to generate visualization: {exc}")
        raise typer.Exit(code=_VISUALIZATION_ERROR_EXIT) from exc

    console.print(f"[green]✓ Generated visualization:[/] {image_path}")

    _render_optimal_points(frontier)

    if budget is not None:
        _render_budget_recommendation(frontier, budget)


def _default_output_path(results_path: Path, axis_x: str, axis_y: str) -> Path:
    safe_stem = results_path.stem
    return results_path.with_name(f"{safe_stem}_{axis_y}_vs_{axis_x}_pareto.png")


def _render_optimal_points(frontier: ParetoFrontier) -> None:
    console.print("\n[bold]Pareto-optimal configurations:[/]")
    for point in sorted(frontier.optimal_points, key=lambda item: item.test_number):
        console.print("  " + _format_point(point, frontier.x_axis, frontier.y_axis))


def _render_budget_recommendation(frontier: ParetoFrontier, budget: float) -> None:
    if budget < 0:
        console.print("[yellow]⚠ Budget threshold must be non-negative; ignoring value.[/]")
        return

    candidate = frontier.best_within_budget(budget)
    if candidate is None:
        console.print(
            f"[yellow]⚠ No Pareto-optimal configurations within budget ≤ {budget:.3f}.[/]"
        )
        return

    console.print(
        "\n[cyan]Recommendation:[/] "
        + _format_point(candidate, frontier.x_axis, frontier.y_axis)
    )


def _format_point(point: ParetoPoint, x_axis: str, y_axis: str) -> str:
    axis_x_value = _metric_value(point, x_axis)
    axis_y_value = _metric_value(point, y_axis)
    latency_sec = point.latency / 1000.0
    return (
        f"Test #{point.test_number}: {y_axis.title()}={axis_y_value:.3f}, "
        f"{x_axis.title()}={axis_x_value:.4f}, latency={latency_sec:.2f}s"
    )


def _metric_value(point: ParetoPoint, axis: str) -> float:
    if axis == "cost":
        return point.cost
    if axis == "latency":
        return point.latency
    if axis == "quality":
        return point.quality
    if axis == "utility":
        return point.utility
    raise ValueError(f"Unsupported axis '{axis}'.")


__all__ = ["app"]
