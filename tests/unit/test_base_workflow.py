from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel

from tesseract_flow.core.base_workflow import BaseWorkflowService
from tesseract_flow.core.config import WorkflowConfig
from tesseract_flow.core.exceptions import WorkflowExecutionError


class ExampleInput(BaseModel):
    value: int


class ExampleOutput(BaseModel):
    doubled: int


class _CompiledWorkflow:
    def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"doubled": payload["value"] * 2}


class _StateGraph:
    def compile(self) -> _CompiledWorkflow:
        return _CompiledWorkflow()


class ExampleWorkflow(BaseWorkflowService[ExampleInput, ExampleOutput]):
    def _build_workflow(self) -> Any:  # type: ignore[override]
        self._build_count = getattr(self, "_build_count", 0) + 1
        return _StateGraph()

    def _validate_output(self, result: Any) -> ExampleOutput:
        return ExampleOutput.model_validate(result)


class FailingCompiled:
    def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("boom")


class FailingGraph:
    def compile(self) -> FailingCompiled:
        return FailingCompiled()


class FailingWorkflow(BaseWorkflowService[ExampleInput, ExampleOutput]):
    def _build_workflow(self) -> Any:  # type: ignore[override]
        return FailingGraph()

    def _validate_output(self, result: Any) -> ExampleOutput:
        return ExampleOutput.model_validate(result)


def test_base_workflow_run_executes_and_records_metadata() -> None:
    workflow = ExampleWorkflow(config=WorkflowConfig())
    output = workflow.run(ExampleInput(value=3))
    assert output.doubled == 6
    metadata = workflow.last_run_metadata
    assert metadata is not None
    assert metadata["completed_at"] >= metadata["started_at"]
    assert metadata["duration_seconds"] >= 0.0
    assert workflow._build_count == 1

    # Cached compiled graph should be reused
    workflow.run(ExampleInput(value=2))
    assert workflow._build_count == 1


def test_base_workflow_reset_rebuilds_graph() -> None:
    workflow = ExampleWorkflow(config=WorkflowConfig())
    workflow.run(ExampleInput(value=1))
    workflow.reset()
    assert workflow.last_run_metadata is None
    workflow.run(ExampleInput(value=2))
    assert workflow._build_count == 2


def test_base_workflow_wraps_exceptions() -> None:
    workflow = FailingWorkflow(config=WorkflowConfig())
    with pytest.raises(WorkflowExecutionError):
        workflow.run(ExampleInput(value=1))
