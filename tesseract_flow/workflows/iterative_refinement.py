"""Iterative refinement workflow for testing DeepSeek R1's self-improvement capabilities.

Tests how R1 refines and improves outputs through multiple revision cycles with feedback.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from langgraph.graph import END, StateGraph
from pydantic import BaseModel, ConfigDict, Field, field_validator

from tesseract_flow.core.base_workflow import BaseWorkflowService
from tesseract_flow.core.config import ExperimentConfig, TestConfiguration, WorkflowConfig
from tesseract_flow.core.strategies import get_strategy


class IterativeRefinementInput(BaseModel):
    """Input payload for iterative refinement task."""

    task_prompt: str = Field(..., min_length=1)
    task_domain: str = Field(..., pattern="^(creative|analytical)$")
    improvement_focus: str = Field(..., pattern="^(quality|conciseness)$")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")

    @field_validator("task_prompt")
    @classmethod
    def _strip_prompt(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "Task prompt must be non-empty."
            raise ValueError(msg)
        return stripped


class IterativeRefinementOutput(BaseModel):
    """Workflow output containing refinement history."""

    initial_output: str
    refinement_iterations: List[Dict[str, str]]
    final_output: str
    evaluation_text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("final_output")
    @classmethod
    def _normalize_output(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "Final output must be non-empty."
            raise ValueError(msg)
        return stripped

    def render_for_evaluation(self) -> str:
        """Return textual representation used for rubric evaluation."""
        return self.evaluation_text


@dataclass
class _RuntimeSettings:
    model: str
    temperature: float
    refinement_iterations: str
    feedback_type: str
    task_domain: str
    improvement_focus: str
    critique_source: str
    convergence_check: str
    metadata: Dict[str, Any]


class IterativeRefinementWorkflow(BaseWorkflowService[IterativeRefinementInput, IterativeRefinementOutput]):
    """LangGraph workflow that tests R1's iterative refinement capabilities."""

    # Sample prompts for different task domains
    CREATIVE_PROMPT = """Write a brief dialogue (3-4 exchanges) between two characters meeting for the first time
at a coffee shop. One is a time traveler, the other a barista who suspects something is off."""

    ANALYTICAL_PROMPT = """Analyze the trade-offs between using a microservices architecture versus a monolithic
architecture for a medium-sized e-commerce platform. Consider scalability, maintenance, and deployment."""

    def __init__(
        self,
        *,
        config: Optional[WorkflowConfig] = None,
        default_model: str = "openrouter/deepseek/deepseek-r1",
        default_temperature: float = 0.6,
    ) -> None:
        super().__init__(config=config)
        self._default_model = default_model
        self._default_temperature = default_temperature
        self._runtime: Optional[_RuntimeSettings] = None

    def prepare_input(
        self,
        test_config: TestConfiguration,
        experiment_config: ExperimentConfig | None,
    ) -> IterativeRefinementInput:
        """Prepare workflow input based on test configuration."""
        values = {str(key): value for key, value in test_config.config_values.items()}
        temperature = self._coerce_float(values.get("temperature"), self._default_temperature)
        model_name = str(values.get("model", self._default_model))
        refinement_iterations = str(values.get("refinement_iterations", "single"))
        feedback_type = str(values.get("feedback_type", "criteria"))
        task_domain = str(values.get("task_domain", "creative"))
        improvement_focus = str(values.get("improvement_focus", "quality"))
        critique_source = str(values.get("critique_source", "self"))
        convergence_check = str(values.get("convergence_check", "none"))

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
            refinement_iterations=refinement_iterations,
            feedback_type=feedback_type,
            task_domain=task_domain,
            improvement_focus=improvement_focus,
            critique_source=critique_source,
            convergence_check=convergence_check,
            metadata=runtime_metadata,
        )

        # Select task prompt based on domain
        task_prompt = self.CREATIVE_PROMPT if task_domain == "creative" else self.ANALYTICAL_PROMPT

        return IterativeRefinementInput(
            task_prompt=task_prompt,
            task_domain=task_domain,
            improvement_focus=improvement_focus,
            metadata=metadata,
        )

    def _build_workflow(self) -> StateGraph:
        """Build LangGraph workflow."""
        graph = StateGraph(dict)
        graph.add_node("initialize", self._initialize_state)
        graph.add_node("generate_initial", self._generate_initial)
        graph.add_node("critique", self._generate_critique)
        graph.add_node("refine", self._refine_output)
        graph.add_node("finalize", self._finalize_output)

        graph.set_entry_point("initialize")
        graph.add_edge("initialize", "generate_initial")
        graph.add_edge("generate_initial", "critique")
        graph.add_edge("critique", "refine")
        graph.add_edge("refine", "finalize")
        graph.add_edge("finalize", END)

        return graph

    def _initialize_state(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        runtime = self._runtime or _RuntimeSettings(
            model=self._default_model,
            temperature=self._default_temperature,
            refinement_iterations="single",
            feedback_type="criteria",
            task_domain="creative",
            improvement_focus="quality",
            critique_source="self",
            convergence_check="none",
            metadata={},
        )
        input_model = IterativeRefinementInput.model_validate(payload)
        return {
            "input": input_model,
            "settings": runtime,
            "initial_output": "",
            "current_output": "",
            "refinement_iterations": [],
            "test_config": runtime.metadata,
        }

    def _generate_initial(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate initial output."""
        runtime: _RuntimeSettings = state["settings"]
        input_model: IterativeRefinementInput = state["input"]

        prompt = f"""Generate a response to the following task:\n\n{input_model.task_prompt}"""

        initial = self._invoke_strategy(prompt, runtime, max_tokens=500)
        state["initial_output"] = initial
        state["current_output"] = initial
        return state

    def _generate_critique(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate critique of current output."""
        runtime: _RuntimeSettings = state["settings"]
        input_model: IterativeRefinementInput = state["input"]
        current_output: str = state["current_output"]

        # Only generate critique if doing multiple iterations
        if runtime.refinement_iterations == "single":
            return state

        focus = input_model.improvement_focus
        feedback_type = runtime.feedback_type

        if feedback_type == "criteria":
            critique_prompt = f"""Review the following output and identify specific ways to improve its {focus}:

Output:
{current_output}

Provide 2-3 specific, actionable improvements focused on {focus}."""
        else:  # comparative
            critique_prompt = f"""Compare the following output to a hypothetical better version with superior {focus}:

Current Output:
{current_output}

What specific changes would make this output significantly better in terms of {focus}?"""

        critique = self._invoke_strategy(critique_prompt, runtime, max_tokens=300)

        return state

    def _refine_output(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Refine output based on critique."""
        runtime: _RuntimeSettings = state["settings"]
        input_model: IterativeRefinementInput = state["input"]
        current_output: str = state["current_output"]
        iterations: List[Dict[str, str]] = state["refinement_iterations"]

        # Only refine if doing multiple iterations
        if runtime.refinement_iterations == "single":
            return state

        # Perform up to 3 refinement iterations
        max_iterations = 3
        for i in range(max_iterations):
            # Generate critique
            critique_prompt = f"""Identify 2-3 specific ways to improve the {input_model.improvement_focus} of this output:

{current_output}"""
            critique = self._invoke_strategy(critique_prompt, runtime, max_tokens=200)

            # Refine based on critique
            refine_prompt = f"""Revise the following output to address these improvements:

Original:
{current_output}

Improvements needed:
{critique}

Provide the improved version:"""
            refined = self._invoke_strategy(refine_prompt, runtime, max_tokens=500)

            iterations.append({
                "iteration": str(i + 1),
                "critique": critique,
                "refined_output": refined,
            })

            current_output = refined

        state["current_output"] = current_output
        state["refinement_iterations"] = iterations
        return state

    def _finalize_output(self, state: Dict[str, Any]) -> IterativeRefinementOutput:
        initial: str = state.get("initial_output") or "(no initial output)"
        final: str = state.get("current_output") or "(no final output)"
        iterations: List[Dict[str, str]] = state.get("refinement_iterations", [])
        input_model: IterativeRefinementInput = state["input"]
        runtime: _RuntimeSettings = state["settings"]

        # Build evaluation text
        eval_parts = [
            f"Task Domain: {runtime.task_domain}",
            f"Improvement Focus: {runtime.improvement_focus}",
            f"Refinement Mode: {runtime.refinement_iterations}",
            f"Iterations Performed: {len(iterations)}",
            f"\nInitial Output:\n{initial}",
        ]

        for iteration in iterations:
            eval_parts.append(f"\n--- Iteration {iteration['iteration']} ---")
            eval_parts.append(f"Critique: {iteration['critique']}")
            eval_parts.append(f"Refined: {iteration['refined_output']}")

        eval_parts.append(f"\nFinal Output:\n{final}")

        evaluation_text = "\n".join(eval_parts)

        return IterativeRefinementOutput(
            initial_output=initial,
            refinement_iterations=iterations,
            final_output=final,
            evaluation_text=evaluation_text,
            metadata=input_model.metadata,
        )

    def _validate_output(self, result: Any) -> IterativeRefinementOutput:
        return IterativeRefinementOutput.model_validate(result)

    def _invoke_strategy(self, prompt: str, runtime: _RuntimeSettings, max_tokens: int = 500) -> str:
        """Invoke generation strategy synchronously."""
        strategy = get_strategy("standard")
        parameters = {
            "temperature": runtime.temperature,
            "max_tokens": max_tokens,
        }
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
