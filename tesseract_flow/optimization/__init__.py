"""Optimization utilities for experiment results."""

from importlib import import_module
from typing import TYPE_CHECKING, Any

from tesseract_flow.optimization.utility import UtilityFunction

if TYPE_CHECKING:  # pragma: no cover - used for type checking only
    from tesseract_flow.optimization.pareto import ParetoFrontier, ParetoPoint

__all__ = ["ParetoFrontier", "ParetoPoint", "UtilityFunction"]


def __getattr__(name: str) -> Any:
    if name in {"ParetoFrontier", "ParetoPoint"}:
        module = import_module("tesseract_flow.optimization.pareto")
        return getattr(module, name)
    msg = f"module 'tesseract_flow.optimization' has no attribute '{name}'"
    raise AttributeError(msg)
