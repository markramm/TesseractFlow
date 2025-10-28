"""Reasoning transparency workflow for testing DeepSeek R1's native reasoning capabilities.

Tests how R1's native reasoning compares to explicitly prompted Chain-of-Thought across
different problem complexities, visibility preferences, and task types.
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


class ReasoningTransparencyInput(BaseModel):
    """Input payload for reasoning transparency task."""

    problem_description: str = Field(..., min_length=1)
    problem_complexity: str = Field(..., pattern="^(simple|complex)$")
    task_type: str = Field(..., pattern="^(analytical|creative)$")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")

    @field_validator("problem_description")
    @classmethod
    def _strip_description(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "Problem description must be non-empty."
            raise ValueError(msg)
        return stripped


class ReasoningTransparencyOutput(BaseModel):
    """Workflow output containing reasoning solution."""

    reasoning_trace: str
    solution: str
    evaluation_text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("reasoning_trace")
    @classmethod
    def _normalize_trace(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "Reasoning trace must be non-empty."
            raise ValueError(msg)
        return stripped

    @field_validator("solution")
    @classmethod
    def _normalize_solution(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "Solution must be non-empty."
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
    reasoning_mode: str
    problem_complexity: str
    reasoning_visibility: str
    task_type: str
    max_reasoning_tokens: str
    verification_step: str
    metadata: Dict[str, Any]


class ReasoningTransparencyWorkflow(BaseWorkflowService[ReasoningTransparencyInput, ReasoningTransparencyOutput]):
    """LangGraph workflow that tests R1's reasoning capabilities.

    Tests how DeepSeek R1's native reasoning compares to prompted Chain-of-Thought
    across problem complexity, visibility preferences, and task types.
    """

    DEFAULT_PROMPTS: Dict[str, str] = {
        "native_r1_visible": (
            "Solve the following problem. Use your natural reasoning process and show your work.\\n"
            "\\n"
            "Problem: {{problem_description}}\\n"
            "\\n"
            "Think through this step by step, then provide your final answer.\\n"
        ),
        "native_r1_hidden": (
            "Solve the following problem directly.\\n"
            "\\n"
            "Problem: {{problem_description}}\\n"
            "\\n"
            "Provide your answer concisely.\\n"
        ),
        "prompted_cot_visible": (
            "Solve the following problem using Chain-of-Thought reasoning.\\n"
            "\\n"
            "Problem: {{problem_description}}\\n"
            "\\n"
            "Let's solve this step by step:\\n"
            "1. First, identify what we know\\n"
            "2. Then, determine what we need to find\\n"
            "3. Finally, work through the solution methodically\\n"
            "\\n"
            "Show all your reasoning steps before giving the final answer.\\n"
        ),
        "prompted_cot_hidden": (
            "Solve the following problem. Think carefully but provide only your final answer.\\n"
            "\\n"
            "Problem: {{problem_description}}\\n"
            "\\n"
            "Answer:\\n"
        ),
    }

    PROBLEMS: Dict[str, Dict[str, str]] = {
        "simple_analytical": "A train travels 120 km in 2 hours. What is its average speed in km/h?",
        "complex_analytical": (
            "Three friends split a restaurant bill. Alice pays 40% of the total, "
            "Bob pays $15 more than Carol, and Carol pays $25. What is the total bill, "
            "and how much does each person pay?"
        ),
        "simple_creative": (
            "A character finds a mysterious key in their attic. "
            "What might this key open, and why is it significant?"
        ),
        "complex_creative": (
            "A detective investigating a theft discovers that the main suspect has an airtight alibi, "
            "yet all evidence points to them. How might the detective resolve this paradox? "
            "Consider multiple possibilities and evaluate which is most plausible."
        ),
    }

    def __init__(
        self,
        *,
        config: Optional[WorkflowConfig] = None,
        default_model: str = "openrouter/deepseek/deepseek-r1",
        default_temperature: float = 0.3,
    ) -> None:
        super().__init__(config=config)
        self._default_model = default_model
        self._default_temperature = default_temperature
        self._runtime: Optional[_RuntimeSettings] = None

    def prepare_input(
        self,
        test_config: TestConfiguration,
        experiment_config: ExperimentConfig | None,
    ) -> ReasoningTransparencyInput:
        """Prepare workflow input based on test configuration."""
        values = {str(key): value for key, value in test_config.config_values.items()}
        temperature = self._coerce_float(values.get("temperature"), self._default_temperature)
        model_name = str(values.get("model", self._default_model))
        reasoning_mode = str(values.get("reasoning_mode", "native_r1"))
        problem_complexity = str(values.get("problem_complexity", "simple"))
        reasoning_visibility = str(values.get("reasoning_visibility", "visible"))
        task_type = str(values.get("task_type", "analytical"))
        max_reasoning_tokens = str(values.get("max_reasoning_tokens", "standard"))
        verification_step = str(values.get("verification_step", "none"))

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
            reasoning_mode=reasoning_mode,
            problem_complexity=problem_complexity,
            reasoning_visibility=reasoning_visibility,
            task_type=task_type,
            max_reasoning_tokens=max_reasoning_tokens,
            verification_step=verification_step,
            metadata=runtime_metadata,
        )

        # Select problem based on complexity and task type
        problem_key = f"{problem_complexity}_{task_type}"
        problem_description = self.PROBLEMS.get(problem_key, self.PROBLEMS["simple_analytical"])

        return ReasoningTransparencyInput(
            problem_description=problem_description,
            problem_complexity=problem_complexity,
            task_type=task_type,
            metadata=metadata,
        )

    def _build_workflow(self) -> StateGraph:
        """Build LangGraph workflow."""
        graph = StateGraph(dict)
        graph.add_node("initialize", self._initialize_state)
        graph.add_node("solve", self._solve_problem)
        graph.add_node("verify", self._verify_solution)
        graph.add_node("finalize", self._finalize_output)

        graph.set_entry_point("initialize")
        graph.add_edge("initialize", "solve")
        graph.add_edge("solve", "verify")
        graph.add_edge("verify", "finalize")
        graph.add_edge("finalize", END)

        return graph

    def _initialize_state(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        runtime = self._runtime or _RuntimeSettings(
            model=self._default_model,
            temperature=self._default_temperature,
            reasoning_mode="native_r1",
            problem_complexity="simple",
            reasoning_visibility="visible",
            task_type="analytical",
            max_reasoning_tokens="standard",
            verification_step="none",
            metadata={},
        )
        input_model = ReasoningTransparencyInput.model_validate(payload)
        return {
            "input": input_model,
            "settings": runtime,
            "reasoning_trace": "",
            "solution": "",
            "test_config": runtime.metadata,
        }

    def _solve_problem(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Solve the problem with configured reasoning mode."""
        runtime: _RuntimeSettings = state["settings"]
        input_model: ReasoningTransparencyInput = state["input"]

        # Select prompt based on reasoning mode and visibility
        prompt_key = f"{runtime.reasoning_mode}_{runtime.reasoning_visibility}"
        template = Template(self.DEFAULT_PROMPTS.get(prompt_key, self.DEFAULT_PROMPTS["native_r1_visible"]))

        # Build context for prompt
        context = {
            "problem_description": input_model.problem_description,
        }

        # Render prompt
        prompt = template.render(**context)

        # Generate with appropriate token limit
        max_tokens = 2000 if runtime.max_reasoning_tokens == "extended" else 1000
        result = self._invoke_strategy(prompt, runtime, max_tokens=max_tokens)

        # Parse reasoning trace and solution
        if runtime.reasoning_visibility == "visible":
            # Try to split reasoning from answer
            if "Answer:" in result or "Final answer:" in result:
                parts = result.split("Answer:" if "Answer:" in result else "Final answer:", 1)
                reasoning_trace = parts[0].strip()
                solution = parts[1].strip() if len(parts) > 1 else result
            else:
                reasoning_trace = result
                solution = result
        else:
            reasoning_trace = "(reasoning hidden)"
            solution = result

        state.update({
            "reasoning_trace": reasoning_trace,
            "solution": solution,
        })
        return state

    def _verify_solution(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Optionally verify the solution."""
        runtime: _RuntimeSettings = state["settings"]

        if runtime.verification_step == "none":
            return state

        input_model: ReasoningTransparencyInput = state["input"]
        solution: str = state["solution"]

        verification_prompt = f"""Review this solution for correctness:

Problem: {input_model.problem_description}

Proposed solution: {solution}

Is this solution correct? If there are errors, identify them briefly.
"""

        verification = self._invoke_strategy(verification_prompt, runtime, max_tokens=300)

        # Append verification to reasoning trace
        current_trace = state["reasoning_trace"]
        state["reasoning_trace"] = f"{current_trace}\n\nVerification: {verification}"

        return state

    def _finalize_output(self, state: Dict[str, Any]) -> ReasoningTransparencyOutput:
        reasoning_trace: str = state.get("reasoning_trace") or "(no reasoning trace)"
        solution: str = state.get("solution") or "No solution generated."
        input_model: ReasoningTransparencyInput = state["input"]
        runtime: _RuntimeSettings = state["settings"]

        evaluation_text = (
            f"Problem Complexity: {runtime.problem_complexity}\n"
            f"Task Type: {runtime.task_type}\n"
            f"Reasoning Mode: {runtime.reasoning_mode}\n"
            f"Visibility: {runtime.reasoning_visibility}\n\n"
            f"Problem: {input_model.problem_description}\n\n"
            f"Reasoning:\n{reasoning_trace}\n\n"
            f"Solution:\n{solution}"
        )

        return ReasoningTransparencyOutput(
            reasoning_trace=reasoning_trace,
            solution=solution,
            evaluation_text=evaluation_text,
            metadata=input_model.metadata,
        )

    def _validate_output(self, result: Any) -> ReasoningTransparencyOutput:
        return ReasoningTransparencyOutput.model_validate(result)

    def _invoke_strategy(self, prompt: str, runtime: _RuntimeSettings, max_tokens: int = 1000) -> str:
        """Invoke generation strategy synchronously."""
        strategy = get_strategy("standard")
        parameters = {
            "temperature": runtime.temperature,
            "max_tokens": max_tokens,
        }

        # Add reasoning parameters based on model type and configuration
        model_lower = runtime.model.lower()
        reasoning_mode = runtime.reasoning_mode

        if ("v3.2" in model_lower or "v3-2" in model_lower) and reasoning_mode == "native_r1":
            # DeepSeek V3.2 uses reasoning.enabled boolean parameter
            parameters["reasoning.enabled"] = True
        elif "r1" in model_lower and reasoning_mode == "native_r1":
            # DeepSeek R1 uses reasoning_mode parameter
            parameters["reasoning_mode"] = "native_r1"

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
