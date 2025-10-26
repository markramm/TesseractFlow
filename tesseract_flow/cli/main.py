"""Typer application wiring for the TesseractFlow CLI."""
from __future__ import annotations

import logging
from typing import Dict

import typer

from tesseract_flow import __version__

from . import experiment, visualize

app = typer.Typer(help="TesseractFlow command line interface")
app.add_typer(experiment.app, name="experiment", help="Run and manage experiments")
app.add_typer(visualize.app, name="visualize", help="Generate experiment visualizations")


def _version_callback(value: bool) -> bool:
    if value:
        from rich.console import Console

        console = Console()
        console.print(f"TesseractFlow {__version__}")
        raise typer.Exit()
    return value


@app.callback()
def main_callback(
    ctx: typer.Context,
    log_level: str = typer.Option(
        "info",
        "--log-level",
        "-l",
        metavar="LEVEL",
        help="Set global log level (critical, error, warning, info, debug).",
    ),
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the TesseractFlow version and exit.",
    ),
) -> None:
    """Configure global CLI options before executing subcommands."""

    del version  # handled by callback

    ctx.ensure_object(dict)
    obj: Dict[str, object] = ctx.obj
    obj["log_level"] = log_level

    level = log_level.upper()
    if level not in {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}:
        raise typer.BadParameter("Log level must be one of critical, error, warning, info, debug.")

    logging.basicConfig(level=getattr(logging, level), force=False)


def main() -> None:
    """Entrypoint executed by the console script."""

    app()


__all__ = ["app", "main"]
