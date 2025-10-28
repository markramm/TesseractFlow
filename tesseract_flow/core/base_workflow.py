"""Base workflow abstraction built on LangGraph."""
from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from collections import Counter
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Dict, Generic, List, Optional, TypeVar

from langgraph.graph import StateGraph
from pydantic import BaseModel

from .config import WorkflowConfig
from .exceptions import WorkflowExecutionError
from .strategies import get_strategy

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

    # Built-in reasoning and verbalized sampling capabilities

    def generate(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        runtime_settings: Optional[Any] = None,
    ) -> str:
        """Universal generation method with automatic reasoning and verbalized sampling detection.

        Automatically applies reasoning or verbalized sampling based on runtime_settings parameters:
        - reasoning_enabled: Enables native reasoning (DeepSeek R1/V3.2)
        - verbalized_sampling: Applies self-consistency or sample-and-rank
        - Falls back to standard generation if no special capabilities are requested

        Args:
            prompt: The prompt to send to the model
            model: The model identifier (e.g., "openrouter/deepseek/deepseek-r1")
            temperature: Temperature for generation (default: 0.7)
            max_tokens: Maximum tokens to generate (default: 1000)
            runtime_settings: Optional runtime settings object with reasoning/sampling parameters

        Returns:
            Generated text with capabilities automatically applied based on settings
        """
        # Extract settings from runtime_settings object or use defaults
        reasoning_enabled = getattr(runtime_settings, "reasoning_enabled", False) if runtime_settings else False
        verbalized_sampling = getattr(runtime_settings, "verbalized_sampling", "none") if runtime_settings else "none"

        # Apply reasoning if enabled
        if reasoning_enabled:
            reasoning_visibility = getattr(runtime_settings, "reasoning_visibility", "visible") if runtime_settings else "visible"
            max_reasoning_tokens = getattr(runtime_settings, "max_reasoning_tokens", 1000) if runtime_settings else 1000
            return self._generate_with_reasoning(
                prompt=prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_reasoning_tokens,
                reasoning_visibility=reasoning_visibility,
            )

        # Apply verbalized sampling if configured
        if verbalized_sampling and verbalized_sampling != "none":
            n_samples = getattr(runtime_settings, "n_samples", 3) if runtime_settings else 3

            if verbalized_sampling == "self_consistency":
                return self._generate_with_self_consistency(
                    prompt=prompt,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    n_samples=n_samples,
                )
            elif verbalized_sampling == "sample_and_rank":
                evaluator_model = getattr(runtime_settings, "model", model) if runtime_settings else model
                return self._generate_with_sample_and_rank(
                    prompt=prompt,
                    model=model,
                    evaluator_model=evaluator_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    n_samples=n_samples,
                )

        # Standard generation
        return self._generate_standard(prompt, model, temperature, max_tokens)

    def _generate_with_reasoning(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        reasoning_visibility: str,
    ) -> str:
        """Generate text with reasoning enabled based on model capabilities.

        Automatically detects model type and applies appropriate reasoning parameters:
        - DeepSeek R1: Uses `reasoning_mode: "native_r1"`
        - DeepSeek V3.2: Uses `reasoning.enabled: true`
        - Other models: Falls back to Chain-of-Thought prompting
        """
        strategy = get_strategy("standard")
        parameters: Dict[str, Any] = {
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # Detect model type and apply reasoning parameters
        model_lower = model.lower()

        if "v3.2" in model_lower or "v3-2" in model_lower:
            # DeepSeek V3.2 uses reasoning.enabled boolean parameter
            parameters["reasoning.enabled"] = True
        elif "r1" in model_lower:
            # DeepSeek R1 uses reasoning_mode parameter
            parameters["reasoning_mode"] = "native_r1"
        else:
            # Fall back to prompted CoT for other models
            if reasoning_visibility == "visible":
                prompt = (
                    "Think step-by-step and show your reasoning before providing the final answer.\\n\\n"
                    f"{prompt}"
                )

        return self._await_coroutine(
            strategy.generate(
                prompt,
                model=model,
                config=parameters,
            )
        )

    def _generate_with_self_consistency(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        n_samples: int,
    ) -> str:
        """Generate multiple samples and return the most common answer (self-consistency).

        Useful for problems with definitive answers where multiple reasoning paths
        should converge on the same solution.
        """
        samples = []
        for _ in range(n_samples):
            sample = self._generate_standard(prompt, model, temperature, max_tokens)
            samples.append(sample)

        # Extract final answers and find most common
        answers = [self._extract_final_answer(sample) for sample in samples]

        # Count occurrences
        answer_counts = Counter(answers)
        most_common_answer, _ = answer_counts.most_common(1)[0]

        return most_common_answer

    def _generate_with_sample_and_rank(
        self,
        prompt: str,
        model: str,
        evaluator_model: str,
        temperature: float,
        max_tokens: int,
        n_samples: int,
    ) -> str:
        """Generate multiple samples and use an evaluator to rank them.

        Generates multiple candidate responses and uses a separate evaluator model
        to rank them based on quality criteria.
        """
        samples = []
        for _ in range(n_samples):
            sample = self._generate_standard(prompt, model, temperature, max_tokens)
            samples.append(sample)

        # Rank samples
        ranked_samples = self._rank_samples(
            samples=samples,
            original_prompt=prompt,
            evaluator_model=evaluator_model,
        )

        # Return the highest-ranked sample
        return ranked_samples[0] if ranked_samples else samples[0]

    def _generate_standard(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Generate a single sample using standard generation."""
        strategy = get_strategy("standard")
        parameters: Dict[str, Any] = {
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        return self._await_coroutine(
            strategy.generate(
                prompt,
                model=model,
                config=parameters,
            )
        )

    def _extract_final_answer(self, text: str) -> str:
        """Extract the final answer from a response.

        Looks for common answer markers or returns the last sentence.
        """
        for marker in ["Answer:", "Final answer:", "Solution:", "Therefore,"]:
            if marker in text:
                parts = text.split(marker, 1)
                if len(parts) > 1:
                    # Return everything after the marker
                    answer = parts[1].strip()
                    # Take first sentence after marker as the answer
                    sentences = answer.split(".")
                    return sentences[0].strip() if sentences else answer

        # If no marker, return the last sentence
        sentences = text.strip().split(".")
        return sentences[-1].strip() if sentences else text.strip()

    def _rank_samples(
        self,
        samples: List[str],
        original_prompt: str,
        evaluator_model: str,
    ) -> List[str]:
        """Rank samples using an evaluator model.

        Returns samples sorted from best to worst.
        """
        criteria = "accuracy, coherence, and completeness"
        ranking_prompt = (
            f"Rank the following {len(samples)} responses to this question based on {criteria}.\\n\\n"
            f"Question: {original_prompt}\\n\\n"
        )

        for i, sample in enumerate(samples, 1):
            ranking_prompt += f"Response {i}:\\n{sample}\\n\\n"

        ranking_prompt += (
            f"Rank these responses from best to worst. "
            f"Provide your ranking as a comma-separated list of numbers (e.g., '3,1,2' means "
            f"response 3 is best, response 1 is second, response 2 is worst).\\n\\n"
            f"Ranking:"
        )

        ranking_response = self._generate_standard(
            prompt=ranking_prompt,
            model=evaluator_model,
            temperature=0.1,  # Low temperature for consistent ranking
            max_tokens=100,
        )

        # Parse ranking (expecting format like "3,1,2")
        try:
            ranking_str = ranking_response.strip().split("\\n")[0]  # Take first line
            # Remove any non-numeric characters except commas
            ranking_str = "".join(c for c in ranking_str if c.isdigit() or c == ",")
            ranking = [int(x.strip()) - 1 for x in ranking_str.split(",") if x.strip()]  # Convert to 0-indexed

            # Validate ranking
            if len(ranking) == len(samples) and set(ranking) == set(range(len(samples))):
                return [samples[i] for i in ranking]
        except (ValueError, IndexError):
            pass

        # If ranking parsing fails, return samples in original order
        return samples

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
