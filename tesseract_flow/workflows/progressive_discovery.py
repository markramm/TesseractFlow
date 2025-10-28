"""Progressive discovery workflow built on LangGraph."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

from jinja2 import Template
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, ConfigDict, Field

from tesseract_flow.core.base_workflow import BaseWorkflowService
from tesseract_flow.core.config import ExperimentConfig, TestConfiguration, WorkflowConfig
from tesseract_flow.core.strategies import get_strategy


class ProgressiveDiscoveryInput(BaseModel):
    """Input for progressive discovery workflow."""

    task_description: str = Field(..., min_length=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    model_config = ConfigDict(extra="allow")


class ProgressiveDiscoveryOutput(BaseModel):
    """Output containing discovered content."""

    discovered_content: str
    evaluation_text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    model_config = ConfigDict(validate_assignment=True)

    def render_for_evaluation(self) -> str:
        return self.evaluation_text


@dataclass
class _RuntimeSettings:
    model: str
    temperature: float
    context_strategy: str
    discovery_trigger: str
    strategy_name: str
    metadata: Dict[str, Any]


class ProgressiveDiscoveryWorkflow(BaseWorkflowService[ProgressiveDiscoveryInput, ProgressiveDiscoveryOutput]):
    """LangGraph workflow for progressive context discovery."""

    DEFAULT_PROMPTS: Dict[str, str] = {
        "discover": (
            "Complete the following task: {{task_description}}\n\n"
            "{% if context_strategy == 'progressive_discovery' %}"
            "Request additional context only when needed. Be efficient.\n"
            "{% else %}"
            "All context is provided upfront.\n"
            "{% endif %}"
            "{% if discovery_trigger == 'explicit_prompts' %}"
            "Use explicit requests like 'I need more information about X' when context is missing.\n"
            "{% else %}"
            "Decide autonomously when you need more context.\n"
            "{% endif %}"
        ),
    }

    def __init__(self, *, config: Optional[WorkflowConfig] = None, default_model: str = "openrouter/deepseek/deepseek-chat", default_temperature: float = 0.6) -> None:
        super().__init__(config=config)
        self._default_model = default_model
        self._default_temperature = default_temperature
        self._runtime: Optional[_RuntimeSettings] = None

    def prepare_input(self, test_config: TestConfiguration, experiment_config: ExperimentConfig | None) -> ProgressiveDiscoveryInput:
        values = {str(key): value for key, value in test_config.config_values.items()}
        self._runtime = _RuntimeSettings(
            model=str(values.get("model", self._default_model)),
            temperature=self._coerce_float(values.get("temperature"), self._default_temperature),
            context_strategy=str(values.get("context_strategy", "full_upfront")),
            discovery_trigger=str(values.get("discovery_trigger", "model_decides")),
            strategy_name=str(values.get("generation_strategy", "standard")),
            metadata={"test_number": test_config.test_number, "config": dict(values)},
        )
        return ProgressiveDiscoveryInput(task_description="Summarize a complex story with minimal context", metadata={"test_number": test_config.test_number, "config_values": dict(values)})

    def _build_workflow(self) -> StateGraph:
        graph: StateGraph = StateGraph(dict)
        graph.add_node("initialize", self._initialize_state)
        graph.add_node("discover", self._discover_content)
        graph.add_node("finalize", self._finalize_output)
        graph.set_entry_point("initialize")
        graph.add_edge("initialize", "discover")
        graph.add_edge("discover", "finalize")
        graph.add_edge("finalize", END)
        return graph

    def _validate_output(self, result: Any) -> ProgressiveDiscoveryOutput:
        return ProgressiveDiscoveryOutput.model_validate(result)

    def _initialize_state(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        runtime = self._runtime or _RuntimeSettings(self._default_model, self._default_temperature, "full_upfront", "model_decides", "standard", {})
        return {"input": ProgressiveDiscoveryInput.model_validate(payload), "settings": runtime, "discovered_content": "", "test_config": runtime.metadata}

    def _discover_content(self, state: Dict[str, Any]) -> Dict[str, Any]:
        runtime: _RuntimeSettings = state["settings"]
        input_model: ProgressiveDiscoveryInput = state["input"]
        prompt = self._render_prompt("discover", {"task_description": input_model.task_description, "context_strategy": runtime.context_strategy, "discovery_trigger": runtime.discovery_trigger})
        discovered_content = self._invoke_strategy(prompt, runtime)
        state.update({"discovered_content": discovered_content})
        return state

    def _finalize_output(self, state: Dict[str, Any]) -> ProgressiveDiscoveryOutput:
        discovered_content = state.get("discovered_content") or "No content discovered."
        return ProgressiveDiscoveryOutput(
            discovered_content=discovered_content,
            evaluation_text=f"Discovered Content:\n{discovered_content}",
            metadata={"strategy": state["settings"].strategy_name, "model": state["settings"].model, "temperature": state["settings"].temperature, "context_strategy": state["settings"].context_strategy, "discovery_trigger": state["settings"].discovery_trigger},
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


__all__ = ["ProgressiveDiscoveryInput", "ProgressiveDiscoveryOutput", "ProgressiveDiscoveryWorkflow"]
