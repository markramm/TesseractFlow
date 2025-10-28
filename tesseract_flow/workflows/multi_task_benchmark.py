"""Multi-task benchmark workflow for testing thinking styles across task types.

This workflow tests whether chain-of-thought, few-shot, and other generation strategies
work better for analytical tasks vs. creative tasks.
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


class MultiTaskBenchmarkInput(BaseModel):
    """Input payload for multi-task benchmark."""

    task_description: str = Field(..., min_length=1)
    task_type: str = "analytical"  # analytical or creative
    expected_output_format: Optional[str] = "freeform"
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


class MultiTaskBenchmarkOutput(BaseModel):
    """Workflow output containing task completion result."""

    task_result: str
    evaluation_text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("task_result")
    @classmethod
    def _normalize_result(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "Task result must be non-empty."
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
    generation_strategy: str
    task_type: str
    example_count: int
    reasoning_visibility: str
    output_format: str
    metadata: Dict[str, Any]


class MultiTaskBenchmarkWorkflow(BaseWorkflowService[MultiTaskBenchmarkInput, MultiTaskBenchmarkOutput]):
    """LangGraph workflow that tests different thinking styles across task types.

    Tests whether CoT, few-shot, and other strategies work better for analytical
    reasoning vs. creative generation tasks.
    """

    DEFAULT_PROMPTS: Dict[str, str] = {
        "execute_task": (
            "You are an AI assistant completing a task.\n"
            "\n"
            "Task Type: {{task_type}}\n"
            "Task Description: {{task_description}}\n"
            "\n"
            "{% if example_count > 0 %}Here are {{example_count}} example(s) of similar tasks:\n"
            "{% if task_type == 'analytical' %}"
            "Example 1: Analyze the logic error in this code: `if x > 5 and x < 3: return True`\n"
            "Answer: This condition can never be true because x cannot be both greater than 5 and less than 3 simultaneously. This is a logical impossibility.\n"
            "{% if example_count == 2 %}"
            "Example 2: What's wrong with this argument: 'All cats have tails. Fluffy has a tail. Therefore, Fluffy is a cat.'\n"
            "Answer: This commits the fallacy of affirming the consequent. Just because cats have tails doesn't mean everything with a tail is a cat.\n"
            "{% endif %}"
            "{% else %}"
            "Example 1: Write a haiku about rain.\n"
            "Answer: Gentle drops descend / Silver threads from clouded sky / Earth drinks, renewed life\n"
            "{% if example_count == 2 %}"
            "Example 2: Create a metaphor for time.\n"
            "Answer: Time is a river, flowing ever forward, carrying moments like leaves on its current.\n"
            "{% endif %}"
            "{% endif %}\n{% endif %}"
            "\n"
            "{% if reasoning_visibility == 'explicit_chain' %}"
            "Show your reasoning step by step before providing the final answer.\n"
            "{% elif reasoning_visibility == 'silent_thinking' %}"
            "Think through the problem carefully, but only provide the final answer.\n"
            "{% endif %}"
            "\n"
            "{% if output_format == 'structured' %}"
            "Provide your answer in this structured format:\n"
            "## Analysis\n"
            "[Your reasoning here]\n\n"
            "## Conclusion\n"
            "[Your final answer here]\n"
            "{% else %}"
            "Provide your answer in a clear, natural format.\n"
            "{% endif %}"
            "\n"
            "Complete the task now:\n"
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
    ) -> MultiTaskBenchmarkInput:
        """Prepare workflow input based on test configuration."""
        values = {str(key): value for key, value in test_config.config_values.items()}
        temperature = self._coerce_float(values.get("temperature"), self._default_temperature)
        model_name = str(values.get("model", self._default_model))
        generation_strategy = str(values.get("generation_strategy", "standard"))
        task_type = str(values.get("task_type", "analytical"))
        example_count = int(values.get("example_count", 0))
        reasoning_visibility = str(values.get("reasoning_visibility", "silent_thinking"))
        output_format = str(values.get("output_format", "freeform"))

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
            generation_strategy=generation_strategy,
            task_type=task_type,
            example_count=example_count,
            reasoning_visibility=reasoning_visibility,
            output_format=output_format,
            metadata=runtime_metadata,
        )

        # Select task based on task type
        if task_type == "analytical":
            task_description = "Analyze the following argument for logical fallacies: 'Studies show that 80% of successful entrepreneurs wake up before 6am. Therefore, if you want to be successful, you must wake up before 6am.'"
        else:  # creative
            task_description = "Write a short paragraph describing a futuristic city where nature and technology have merged seamlessly. Focus on sensory details and atmosphere."

        return MultiTaskBenchmarkInput(
            task_description=task_description,
            task_type=task_type,
            expected_output_format=output_format,
            metadata=metadata,
        )

    def _build_workflow(self) -> StateGraph:
        """Build LangGraph workflow."""
        graph = StateGraph(dict)
        graph.add_node("initialize", self._initialize_state)
        graph.add_node("execute", self._execute_task)
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
            generation_strategy="standard",
            task_type="analytical",
            example_count=0,
            reasoning_visibility="silent_thinking",
            output_format="freeform",
            metadata={},
        )
        input_model = MultiTaskBenchmarkInput.model_validate(payload)
        return {
            "input": input_model,
            "settings": runtime,
            "task_result": "",
            "test_config": runtime.metadata,
        }

    def _execute_task(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the task using configured thinking style."""
        runtime: _RuntimeSettings = state["settings"]
        input_model: MultiTaskBenchmarkInput = state["input"]

        # Get strategy
        strategy: GenerationStrategy = get_strategy(runtime.generation_strategy)

        # Build context for prompt
        context = {
            "task_description": input_model.task_description,
            "task_type": runtime.task_type,
            "example_count": runtime.example_count,
            "reasoning_visibility": runtime.reasoning_visibility,
            "output_format": runtime.output_format,
        }

        # Render prompt
        template = Template(self.DEFAULT_PROMPTS["execute_task"])
        prompt = template.render(**context)

        # Generate
        task_result = self._invoke_strategy(prompt, runtime)

        state.update({
            "task_result": task_result,
        })
        return state

    def _finalize_output(self, state: Dict[str, Any]) -> MultiTaskBenchmarkOutput:
        task_result: str = state.get("task_result") or "No result generated."
        input_model: MultiTaskBenchmarkInput = state["input"]
        runtime: _RuntimeSettings = state["settings"]

        evaluation_text = f"Task: {input_model.task_description}\n\nTask Type: {runtime.task_type}\n\nResult:\n{task_result}"

        return MultiTaskBenchmarkOutput(
            task_result=task_result,
            evaluation_text=evaluation_text,
            metadata=input_model.metadata,
        )

    def _validate_output(self, result: Any) -> MultiTaskBenchmarkOutput:
        return MultiTaskBenchmarkOutput.model_validate(result)

    def _invoke_strategy(self, prompt: str, runtime: _RuntimeSettings) -> str:
        """Invoke generation strategy synchronously."""
        strategy = get_strategy(runtime.generation_strategy)
        parameters = {"temperature": runtime.temperature}
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
