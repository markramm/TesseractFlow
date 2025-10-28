"""Multi-domain tasks workflow for temperature and sampling parameter mapping.

Tests how temperature, top_p, repetition penalty, and other sampling parameters affect
different task types (creative writing vs. data extraction).
"""
from __future__ import annotations

import asyncio

from dataclasses import dataclass
from typing import Any, Dict, Optional

from jinja2 import Template
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, ConfigDict, Field, field_validator

from tesseract_flow.core.base_workflow import BaseWorkflowService
from tesseract_flow.core.config import ExperimentConfig, TestConfiguration, WorkflowConfig
from tesseract_flow.core.exceptions import WorkflowExecutionError
from tesseract_flow.core.strategies import GenerationStrategy, get_strategy


class MultiDomainTaskInput(BaseModel):
    """Input payload for multi-domain task."""

    task_domain: str = Field(..., pattern="^(creative_writing|data_extraction)$")
    task_description: str = Field(..., min_length=1)
    source_content: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")

    @field_validator("task_description")
    @classmethod
    def _strip_description(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "Task description must be non-empty."
            raise ValueError(msg)
        return stripped


class MultiDomainTaskOutput(BaseModel):
    """Workflow output containing task result."""

    task_output: str
    evaluation_text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("task_output")
    @classmethod
    def _normalize_output(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "Task output must be non-empty."
            raise ValueError(msg)
        return stripped

    @field_validator("evaluation_text")
    @classmethod
    def _normalize_evaluation(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "Evaluation text must be non-empty."
            raise ValueError(msg)
        return stripped

    def render_for_evaluation(self) -> str:
        """Return textual representation used for rubric evaluation."""
        return self.evaluation_text


@dataclass
class _RuntimeSettings:
    model: str
    temperature: float
    task_domain: str
    output_length: str
    repetition_penalty: str
    top_p: float
    presence_penalty: float
    frequency_penalty: float
    metadata: Dict[str, Any]


class MultiDomainTaskWorkflow(BaseWorkflowService[MultiDomainTaskInput, MultiDomainTaskOutput]):
    """LangGraph workflow that tests sampling parameters across task domains.

    Tests how temperature, top_p, and penalty settings affect quality and creativity
    in different types of tasks (creative writing vs. structured data extraction).
    """

    DEFAULT_PROMPTS: Dict[str, str] = {
        "creative_writing": (
            "You are a creative fiction writer.\n"
            "\n"
            "Task: {{task_description}}\n"
            "{% if source_content %}Context: {{source_content}}\n{% endif %}"
            "\n"
            "Target length: {{output_length}}\n"
            "\n"
            "Write compelling, original prose that engages the reader. Focus on:\n"
            "- Vivid imagery and sensory details\n"
            "- Natural dialogue and character voice\n"
            "- Emotional resonance\n"
            "- Unexpected but coherent story beats\n"
            "\n"
            "Begin writing:\n"
        ),
        "data_extraction": (
            "You are a precise data extraction specialist.\n"
            "\n"
            "Task: {{task_description}}\n"
            "{% if source_content %}Source Material:\n{{source_content}}\n{% endif %}"
            "\n"
            "Extract the requested information accurately and completely. Focus on:\n"
            "- Precision and factual accuracy\n"
            "- Complete coverage of requested data points\n"
            "- Structured, organized output\n"
            "- No hallucination or speculation\n"
            "\n"
            "{% if output_length == 'short' %}"
            "Provide a concise extraction (2-3 key points).\n"
            "{% else %}"
            "Provide a comprehensive extraction with all relevant details.\n"
            "{% endif %}"
            "\n"
            "Extract the data now:\n"
        ),
    }

    def __init__(
        self,
        *,
        config: Optional[WorkflowConfig] = None,
        default_model: str = "openrouter/deepseek/deepseek-chat",
        default_temperature: float = 0.7,
    ) -> None:
        super().__init__(config=config)
        self._default_model = default_model
        self._default_temperature = default_temperature
        self._runtime: Optional[_RuntimeSettings] = None

    def prepare_input(
        self,
        test_config: TestConfiguration,
        experiment_config: ExperimentConfig | None,
    ) -> MultiDomainTaskInput:
        """Prepare workflow input based on test configuration."""
        values = {str(key): value for key, value in test_config.config_values.items()}
        temperature = self._coerce_float(values.get("temperature"), self._default_temperature)
        model_name = str(values.get("model", self._default_model))
        task_domain = str(values.get("task_domain", "creative_writing"))
        output_length = str(values.get("output_length", "short"))
        repetition_penalty = str(values.get("repetition_penalty", "default"))
        top_p = self._coerce_float(values.get("top_p"), 0.9)
        presence_penalty = self._coerce_float(values.get("presence_penalty"), 0.0)
        frequency_penalty = self._coerce_float(values.get("frequency_penalty"), 0.0)

        metadata = {
            "test_number": test_config.test_number,
            "config_values": dict(values),
        }
        runtime_metadata = {
            "test_number": test_config.test_number,
            "config": dict(values),
        }

        self._runtime = _RuntimeSettings(
            model=model_name,
            temperature=temperature,
            task_domain=task_domain,
            output_length=output_length,
            repetition_penalty=repetition_penalty,
            top_p=top_p,
            presence_penalty=presence_penalty,
            frequency_penalty=frequency_penalty,
            metadata=runtime_metadata,
        )

        # Select task based on domain
        if task_domain == "creative_writing":
            task_description = "Write a scene where a character discovers a hidden truth about their past."
            source_content = None
        else:  # data_extraction
            task_description = "Extract all character names, their ages (if mentioned), and their roles from the text."
            source_content = """Captain Sarah Chen (42) commanded the starship with steady confidence. Her first officer, Lieutenant Marcus Webb, barely twenty-eight but brilliant, monitored the helm. In engineering, Chief Patel oversaw the quantum drive, while Dr. Amara Singh, the ship's medical officer at age 35, tended to the crew's health. Young Ensign Torres, fresh from the academy at twenty-two, managed communications."""

        return MultiDomainTaskInput(
            task_domain=task_domain,
            task_description=task_description,
            source_content=source_content,
            metadata=metadata,
        )

    def _build_workflow(self) -> StateGraph:
        """Build LangGraph workflow."""
        graph = StateGraph(dict)
        graph.add_node("initialize", self._initialize_state)
        graph.add_node("execute", self._execute_domain_task)
        graph.add_node("finalize", self._finalize_output)

        graph.set_entry_point("initialize")
        graph.add_edge("initialize", "execute")
        graph.add_edge("execute", "finalize")
        graph.add_edge("finalize", END)

        return graph

    def _initialize_state(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        runtime = self._runtime or _RuntimeSettings(
            model=self._default_model,
            temperature=self._default_temperature,
            task_domain="creative_writing",
            output_length="short",
            repetition_penalty="default",
            top_p=0.9,
            presence_penalty=0.0,
            frequency_penalty=0.0,
            metadata={},
        )
        input_model = MultiDomainTaskInput.model_validate(payload)
        return {
            "input": input_model,
            "settings": runtime,
            "task_output": "",
            "test_config": runtime.metadata,
        }

    def _execute_domain_task(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute task with configured sampling parameters."""
        runtime: _RuntimeSettings = state["settings"]
        input_model: MultiDomainTaskInput = state["input"]

        # Get strategy
        strategy: GenerationStrategy = get_strategy("standard")

        # Select prompt based on domain
        prompt_key = runtime.task_domain
        template = Template(self.DEFAULT_PROMPTS[prompt_key])

        # Build context for prompt
        context = {
            "task_description": input_model.task_description,
            "source_content": input_model.source_content or "",
            "output_length": runtime.output_length,
        }

        # Render prompt
        prompt = template.render(**context)

        # Generate with sampling parameters
        task_output = self._invoke_strategy(prompt, runtime)

        state.update({
            "task_output": task_output,
        })
        return state

    def _finalize_output(self, state: Dict[str, Any]) -> MultiDomainTaskOutput:
        task_output: str = state.get("task_output") or "No output generated."
        input_model: MultiDomainTaskInput = state["input"]
        runtime: _RuntimeSettings = state["settings"]

        evaluation_text = (
            f"Task Domain: {runtime.task_domain}\n"
            f"Temperature: {runtime.temperature}\n"
            f"Task: {input_model.task_description}\n\n"
            f"Output:\n{task_output}"
        )

        return MultiDomainTaskOutput(
            task_output=task_output,
            evaluation_text=evaluation_text,
            metadata=input_model.metadata,
        )

    def _validate_output(self, result: Any) -> MultiDomainTaskOutput:
        return MultiDomainTaskOutput.model_validate(result)

    def _invoke_strategy(self, prompt: str, runtime: _RuntimeSettings) -> str:
        """Invoke generation strategy synchronously."""
        strategy = get_strategy("standard")
        # Build config with all sampling parameters
        parameters = {"temperature": runtime.temperature}
        if runtime.top_p > 0:
            parameters["top_p"] = runtime.top_p
        if runtime.presence_penalty > 0:
            parameters["presence_penalty"] = runtime.presence_penalty
        if runtime.frequency_penalty > 0:
            parameters["frequency_penalty"] = runtime.frequency_penalty

        return self._await_coroutine(
            strategy.generate(
                prompt,
                model=runtime.model,
                config=parameters,
            )
        )

    @staticmethod
    def _await_coroutine(coroutine: Any) -> str:
        """Execute async coroutine synchronously."""
        try:
            return asyncio.run(coroutine)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(coroutine)
            finally:
                loop.close()

    @staticmethod
    def _coerce_float(value: Any, default: float) -> float:
        """Coerce value to float with fallback."""
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
