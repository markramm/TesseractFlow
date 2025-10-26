"""Base workflow abstraction built on LangGraph."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Generic, Optional, TypeVar

from langgraph.graph import StateGraph
from pydantic import BaseModel

from .config import WorkflowConfig
from .exceptions import WorkflowExecutionError

TInput = TypeVar("TInput", bound=BaseModel)
TOutput = TypeVar("TOutput", bound=BaseModel)

logger = logging.getLogger(__name__)


class BaseWorkflowService(ABC, Generic[TInput, TOutput]):
    """Base class for workflow services orchestrated via LangGraph."""

    def __init__(self, config: Optional[WorkflowConfig] = None) -> None:
        self.config = config or WorkflowConfig()
        self._compiled_graph: Optional[Any] = None
        self._last_run_metadata: dict[str, Any] | None = None

    @abstractmethod
    def _build_workflow(self) -> StateGraph:
        """Construct the LangGraph state graph for the workflow."""

    @abstractmethod
    def _validate_output(self, result: Any) -> TOutput:
        """Validate and coerce the workflow result into the output schema."""

    def _compile_workflow(self) -> Any:
        if self._compiled_graph is None:
            graph = self._build_workflow()
            logger.debug("Compiling workflow %s", self.__class__.__name__)
            self._compiled_graph = graph.compile()
        return self._compiled_graph

    def run(self, input_data: TInput) -> TOutput:
        """Execute the workflow synchronously and return validated output."""

        compiled = self._compile_workflow()
        started_at = datetime.now(tz=timezone.utc)
        start_perf = perf_counter()
        payload = input_data.model_dump(mode="python")

        logger.debug(
            "Executing workflow %s with payload keys: %s",
            self.__class__.__name__,
            ", ".join(sorted(payload.keys())),
        )
        try:
            result = compiled.invoke(payload)
        except Exception as exc:  # pragma: no cover - defensive guard
            raise WorkflowExecutionError("Workflow execution failed") from exc

        duration = perf_counter() - start_perf
        completed_at = datetime.now(tz=timezone.utc)

        output = self._validate_output(result)
        self._last_run_metadata = {
            "started_at": started_at,
            "completed_at": completed_at,
            "duration_seconds": duration,
        }
        logger.debug(
            "Workflow %s completed in %.2f seconds", self.__class__.__name__, duration
        )
        return output

    @property
    def last_run_metadata(self) -> dict[str, Any] | None:
        """Metadata captured from the most recent execution."""

        return self._last_run_metadata

    def reset(self) -> None:
        """Reset cached compiled graph to rebuild workflow on next run."""

        logger.debug("Resetting compiled workflow for %s", self.__class__.__name__)
        self._compiled_graph = None
        self._last_run_metadata = None
