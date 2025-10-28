"""Character development workflow built on LangGraph."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from jinja2 import Template
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, ConfigDict, Field, field_validator

from tesseract_flow.core.base_workflow import BaseWorkflowService
from tesseract_flow.core.config import ExperimentConfig, TestConfiguration, WorkflowConfig
from tesseract_flow.core.exceptions import WorkflowExecutionError
from tesseract_flow.core.strategies import get_strategy


class CharacterDevelopmentInput(BaseModel):
    """Input for character development workflow."""

    character_name: str = Field(..., min_length=1)
    current_state: str = Field(..., min_length=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    model_config = ConfigDict(extra="allow")


class CharacterDevelopmentOutput(BaseModel):
    """Output containing character development."""

    development_text: str
    evaluation_text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    model_config = ConfigDict(validate_assignment=True)

    def render_for_evaluation(self) -> str:
        return self.evaluation_text


@dataclass
class _RuntimeSettings:
    model: str
    temperature: float
    revision_strategy: str
    output_format: str
    strategy_name: str
    metadata: Dict[str, Any]


class CharacterDevelopmentWorkflow(BaseWorkflowService[CharacterDevelopmentInput, CharacterDevelopmentOutput]):
    """LangGraph workflow for character development."""

    DEFAULT_PROMPTS: Dict[str, str] = {
        "develop": (
            "You are a character development specialist. Develop the character:\n\n"
            "Character: {{character_name}}\n"
            "Current State: {{current_state}}\n\n"
            "{% if output_format == 'structured_json' %}"
            "Provide analysis in JSON format with fields: traits, growth, motivations.\n"
            "{% else %}"
            "Provide natural prose analysis of character development.\n"
            "{% endif %}"
            "Focus on continuity, arc progression, and writer utility."
        ),
    }

    def __init__(self, *, config: Optional[WorkflowConfig] = None, default_model: str = "openrouter/deepseek/deepseek-chat", default_temperature: float = 0.5) -> None:
        super().__init__(config=config)
        self._default_model = default_model
        self._default_temperature = default_temperature
        self._runtime: Optional[_RuntimeSettings] = None

    def prepare_input(self, test_config: TestConfiguration, experiment_config: ExperimentConfig | None) -> CharacterDevelopmentInput:
        values = {str(key): value for key, value in test_config.config_values.items()}
        self._runtime = _RuntimeSettings(
            model=str(values.get("model", self._default_model)),
            temperature=self._coerce_float(values.get("temperature"), self._default_temperature),
            revision_strategy=str(values.get("revision_strategy", "refine")),
            output_format=str(values.get("output_format", "freeform")),
            strategy_name=str(values.get("generation_strategy", "standard")),
            metadata={"test_number": test_config.test_number, "config": dict(values)},
        )
        return CharacterDevelopmentInput(character_name="Elena", current_state="facing betrayal", metadata={"test_number": test_config.test_number, "config_values": dict(values)})

    def _build_workflow(self) -> StateGraph:
        graph: StateGraph = StateGraph(dict)
        graph.add_node("initialize", self._initialize_state)
        graph.add_node("develop", self._develop_character)
        graph.add_node("finalize", self._finalize_output)
        graph.set_entry_point("initialize")
        graph.add_edge("initialize", "develop")
        graph.add_edge("develop", "finalize")
        graph.add_edge("finalize", END)
        return graph

    def _validate_output(self, result: Any) -> CharacterDevelopmentOutput:
        return CharacterDevelopmentOutput.model_validate(result)

    def _initialize_state(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        runtime = self._runtime or _RuntimeSettings(self._default_model, self._default_temperature, "refine", "freeform", "standard", {})
        return {"input": CharacterDevelopmentInput.model_validate(payload), "settings": runtime, "development_text": "", "test_config": runtime.metadata}

    def _develop_character(self, state: Dict[str, Any]) -> Dict[str, Any]:
        runtime: _RuntimeSettings = state["settings"]
        input_model: CharacterDevelopmentInput = state["input"]
        prompt = self._render_prompt("develop", {"character_name": input_model.character_name, "current_state": input_model.current_state, "output_format": runtime.output_format})
        development_text = self._invoke_strategy(prompt, runtime)
        state.update({"development_text": development_text})
        return state

    def _finalize_output(self, state: Dict[str, Any]) -> CharacterDevelopmentOutput:
        development_text = state.get("development_text") or "No development generated."
        return CharacterDevelopmentOutput(
            development_text=development_text,
            evaluation_text=f"Character Development:\n{development_text}",
            metadata={"strategy": state["settings"].strategy_name, "model": state["settings"].model, "temperature": state["settings"].temperature, "revision_strategy": state["settings"].revision_strategy, "output_format": state["settings"].output_format},
        )

    def _render_prompt(self, name: str, context: Mapping[str, Any]) -> str:
        return Template(self.DEFAULT_PROMPTS[name]).render(**context).strip()

    def _invoke_strategy(self, prompt: str, runtime: _RuntimeSettings) -> str:
        strategy = get_strategy(runtime.strategy_name)
        try:
            return asyncio.run(strategy.generate(prompt, model=runtime.model, config={"temperature": runtime.temperature}))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(strategy.generate(prompt, model=runtime.model, config={"temperature": runtime.temperature}))
            finally:
                loop.close()

    def _coerce_float(self, value: Any, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default


__all__ = ["CharacterDevelopmentInput", "CharacterDevelopmentOutput", "CharacterDevelopmentWorkflow"]
