"""Custom exception hierarchy for TesseractFlow."""
from typing import Iterable, Optional


class TesseractFlowError(Exception):
    """Base exception for all TesseractFlow errors."""


class ConfigurationError(TesseractFlowError):
    """Raised when configuration validation fails."""

    def __init__(self, message: str, *, details: Optional[Iterable[str]] = None) -> None:
        super().__init__(message)
        self.details = list(details or [])


class ExperimentError(TesseractFlowError):
    """Raised when experiment execution encounters an unrecoverable error."""


class WorkflowError(TesseractFlowError):
    """Raised when workflow execution fails."""


class WorkflowExecutionError(WorkflowError):
    """Specific failure during workflow execution lifecycle."""


class VisualizationError(TesseractFlowError):
    """Raised when Pareto or other visualization rendering fails."""


class EvaluationError(TesseractFlowError):
    """Raised when rubric-based evaluation fails."""


class CacheError(TesseractFlowError):
    """Raised when cache operations fail."""
