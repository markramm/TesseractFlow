"""Integration tests for the code review workflow."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from tesseract_flow.core.config import (
    ExperimentConfig,
    TestConfiguration,
    UtilityWeights,
    Variable,
    WorkflowConfig,
)
from tesseract_flow.workflows import CodeReviewOutput, CodeReviewWorkflow


class _FakeStrategy:
    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []

    async def generate(
        self,
        prompt: str,
        *,
        model: str,
        config: Dict[str, Any] | None = None,
    ) -> str:
        self.calls.append({"prompt": prompt, "model": model, "config": dict(config or {})})
        payload = {
            "summary": "Highlights spacing issues and missing validation.",
            "issues": [
                {
                    "type": "style",
                    "severity": "HIGH",
                    "line_number": "3",
                    "description": "The function body is not formatted with consistent spacing.",
                    "suggestion": "Apply PEP8 formatting and add blank lines.",
                },
                {
                    "type": "bug",
                    "severity": "medium",
                    "description": "Inputs are not validated before use.",
                },
            ],
            "suggestions": [
                "Add input validation to guard against None values.",
                "Format the function with standard Python conventions.",
            ],
        }
        return json.dumps(payload)


def test_code_review_workflow_generates_structured_feedback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    sample_code = """\ndef add(a,b):\n    return a+b\n"""
    sample_path = tmp_path / "sample.py"
    sample_path.write_text(sample_code, encoding="utf-8")

    workflow_config = WorkflowConfig(sample_code_path=str(sample_path))
    workflow = CodeReviewWorkflow(config=workflow_config)

    fake_strategy = _FakeStrategy()
    monkeypatch.setattr(
        "tesseract_flow.workflows.code_review.get_strategy",
        lambda name: fake_strategy,
    )

    experiment_config = ExperimentConfig(
        name="code_review_experiment",
        workflow="code_review",
        variables=[
            Variable(name="temperature", level_1=0.3, level_2=0.7),
            Variable(name="model", level_1="model/a", level_2="model/b"),
            Variable(name="context_size", level_1="file_only", level_2="full_module"),
            Variable(name="generation_strategy", level_1="standard", level_2="chain_of_thought"),
        ],
        utility_weights=UtilityWeights(quality=1.0, cost=0.1, time=0.05),
        workflow_config=workflow_config,
    )

    test_config = TestConfiguration(
        test_number=1,
        config_values={
            "temperature": 0.3,
            "model": "model/a",
            "context_size": "file_only",
            "generation_strategy": "standard",
        },
        workflow="code_review",
    )

    prepared_input = workflow.prepare_input(test_config, experiment_config)
    assert prepared_input.language == "python"
    assert "test_number" in prepared_input.metadata
    assert prepared_input.metadata["config_values"]["model"] == "model/a"

    output = workflow.run(prepared_input)
    assert isinstance(output, CodeReviewOutput)
    assert output.summary.startswith("Identified 2 issues") or "Highlights" in output.summary
    assert len(output.issues) == 2
    assert output.issues[0].severity == "high"
    assert output.issues[0].line_number == 3
    assert output.issues[1].description.startswith("Inputs are not validated")
    assert len(output.suggestions) == 2
    assert "Suggestions:" in output.evaluation_text

    metadata = output.metadata
    assert metadata["strategy"] == "standard"
    assert metadata["model"] == "model/a"
    assert metadata["context_size"] == "file_only"
    assert Path(metadata["sample_code_path"]) == sample_path
    assert workflow.last_run_metadata is not None
    assert fake_strategy.calls[0]["config"]["temperature"] == pytest.approx(0.3)
    assert sample_code.strip() in fake_strategy.calls[0]["prompt"]
