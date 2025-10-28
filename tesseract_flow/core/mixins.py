"""Reusable mixins for adding reasoning and verbalized sampling capabilities to workflows."""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Mapping, Optional

from .strategies import GenerationStrategy, get_strategy


class ReasoningMixin:
    """Mixin to add native reasoning capabilities to any workflow.

    Automatically detects model type and applies appropriate reasoning parameters:
    - DeepSeek R1: Uses `reasoning_mode: "native_r1"`
    - DeepSeek V3.2: Uses `reasoning.enabled: true`
    - Other models: Falls back to Chain-of-Thought prompting

    Example:
        class MyWorkflow(ReasoningMixin, BaseWorkflowService):
            def my_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
                # Enable reasoning for this generation
                response = self.generate_with_reasoning(
                    prompt="Solve this problem...",
                    model="openrouter/deepseek/deepseek-r1",
                    temperature=0.3,
                )
                return {"output": response}
    """

    def generate_with_reasoning(
        self,
        prompt: str,
        *,
        model: str,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        reasoning_visibility: str = "visible",
        additional_params: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate text with reasoning enabled based on model capabilities.

        Args:
            prompt: The prompt to send to the model
            model: The model identifier (e.g., "openrouter/deepseek/deepseek-r1")
            temperature: Temperature for generation (default: 0.3)
            max_tokens: Maximum tokens to generate (default: 1000)
            reasoning_visibility: "visible" to include reasoning trace, "hidden" to suppress (default: "visible")
            additional_params: Additional parameters to pass to the model

        Returns:
            Generated text with or without reasoning trace depending on visibility setting
        """
        strategy = get_strategy("standard")
        parameters: Dict[str, Any] = {
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if additional_params:
            parameters.update(additional_params)

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
                    "Think step-by-step and show your reasoning before providing the final answer.\n\n"
                    f"{prompt}"
                )

        return self._await_coroutine(
            strategy.generate(
                prompt,
                model=model,
                config=parameters,
            )
        )

    def parse_reasoning_and_solution(self, response: str) -> tuple[str, str]:
        """Parse a response into reasoning trace and final solution.

        Looks for markers like "Answer:", "Final answer:", "Solution:" to split
        reasoning from the final answer.

        Args:
            response: The full model response

        Returns:
            Tuple of (reasoning_trace, solution)
        """
        for marker in ["Answer:", "Final answer:", "Solution:", "Final Answer:"]:
            if marker in response:
                parts = response.split(marker, 1)
                reasoning_trace = parts[0].strip()
                solution = parts[1].strip() if len(parts) > 1 else response
                return reasoning_trace, solution

        # If no marker found, treat entire response as both reasoning and solution
        return response, response

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


class VerbalizationMixin:
    """Mixin to add verbalized sampling capabilities (self-consistency, sample-and-rank, ensemble).

    Provides multiple verbalized sampling techniques:
    - Self-consistency: Generate multiple samples and pick most common answer
    - Sample-and-rank: Generate multiple samples and rank by quality
    - Ensemble: Generate multiple samples with different approaches and combine

    Example:
        class MyWorkflow(VerbalizationMixin, BaseWorkflowService):
            def my_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
                # Use self-consistency sampling
                response = self.generate_with_self_consistency(
                    prompt="What is 2+2?",
                    model="openrouter/anthropic/claude-haiku-4.5",
                    n_samples=5,
                )
                return {"output": response}
    """

    def generate_with_self_consistency(
        self,
        prompt: str,
        *,
        model: str,
        n_samples: int = 5,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        additional_params: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate multiple samples and return the most common answer (self-consistency).

        Useful for problems with definitive answers where multiple reasoning paths
        should converge on the same solution.

        Args:
            prompt: The prompt to send to the model
            model: The model identifier
            n_samples: Number of samples to generate (default: 5)
            temperature: Temperature for generation (default: 0.7)
            max_tokens: Maximum tokens per sample (default: 1000)
            additional_params: Additional parameters to pass to the model

        Returns:
            The most frequently occurring answer across all samples
        """
        samples = self._generate_multiple_samples(
            prompt=prompt,
            model=model,
            n_samples=n_samples,
            temperature=temperature,
            max_tokens=max_tokens,
            additional_params=additional_params,
        )

        # Extract final answers and find most common
        answers = [self._extract_final_answer(sample) for sample in samples]

        # Count occurrences
        from collections import Counter
        answer_counts = Counter(answers)
        most_common_answer, _ = answer_counts.most_common(1)[0]

        return most_common_answer

    def generate_with_sample_and_rank(
        self,
        prompt: str,
        *,
        model: str,
        evaluator_model: str,
        n_samples: int = 3,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        ranking_criteria: Optional[str] = None,
        additional_params: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate multiple samples and use an evaluator to rank them.

        Generates multiple candidate responses and uses a separate evaluator model
        to rank them based on specified criteria.

        Args:
            prompt: The prompt to send to the model
            model: The generator model identifier
            evaluator_model: The evaluator model identifier
            n_samples: Number of samples to generate (default: 3)
            temperature: Temperature for generation (default: 0.7)
            max_tokens: Maximum tokens per sample (default: 1000)
            ranking_criteria: Criteria for ranking (default: "accuracy, coherence, and completeness")
            additional_params: Additional parameters to pass to the model

        Returns:
            The highest-ranked sample according to the evaluator
        """
        samples = self._generate_multiple_samples(
            prompt=prompt,
            model=model,
            n_samples=n_samples,
            temperature=temperature,
            max_tokens=max_tokens,
            additional_params=additional_params,
        )

        # Rank samples
        criteria = ranking_criteria or "accuracy, coherence, and completeness"
        ranked_samples = self._rank_samples(
            samples=samples,
            original_prompt=prompt,
            evaluator_model=evaluator_model,
            criteria=criteria,
        )

        # Return the highest-ranked sample
        return ranked_samples[0] if ranked_samples else samples[0]

    def generate_with_ensemble(
        self,
        prompt: str,
        *,
        model: str,
        approaches: Optional[List[str]] = None,
        temperature: float = 0.5,
        max_tokens: int = 1000,
        additional_params: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate samples with different reasoning approaches and synthesize them.

        Uses multiple different prompting strategies (e.g., analytical, creative, step-by-step)
        and synthesizes the results into a single coherent response.

        Args:
            prompt: The base prompt to send to the model
            model: The model identifier
            approaches: List of approach modifiers (default: analytical, creative, methodical)
            temperature: Temperature for generation (default: 0.5)
            max_tokens: Maximum tokens per sample (default: 1000)
            additional_params: Additional parameters to pass to the model

        Returns:
            A synthesized response combining insights from all approaches
        """
        if approaches is None:
            approaches = [
                "Think about this analytically and logically",
                "Think about this creatively and consider novel perspectives",
                "Think about this step-by-step, methodically building your answer",
            ]

        # Generate samples with different approaches
        samples = []
        for approach in approaches:
            modified_prompt = f"{approach}.\n\n{prompt}"
            sample = self._generate_single_sample(
                prompt=modified_prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                additional_params=additional_params,
            )
            samples.append(sample)

        # Synthesize responses
        synthesis_prompt = (
            f"Given these different perspectives on the same question:\n\n"
            f"Original question: {prompt}\n\n"
        )

        for i, (approach, sample) in enumerate(zip(approaches, samples), 1):
            synthesis_prompt += f"Perspective {i} ({approach}):\n{sample}\n\n"

        synthesis_prompt += (
            "Synthesize these perspectives into a single coherent, comprehensive answer "
            "that incorporates the best insights from each approach."
        )

        return self._generate_single_sample(
            prompt=synthesis_prompt,
            model=model,
            temperature=0.3,  # Lower temperature for synthesis
            max_tokens=max_tokens,
            additional_params=additional_params,
        )

    # Private helper methods

    def _generate_multiple_samples(
        self,
        prompt: str,
        model: str,
        n_samples: int,
        temperature: float,
        max_tokens: int,
        additional_params: Optional[Dict[str, Any]],
    ) -> List[str]:
        """Generate multiple samples with the same prompt."""
        samples = []
        for _ in range(n_samples):
            sample = self._generate_single_sample(
                prompt=prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                additional_params=additional_params,
            )
            samples.append(sample)
        return samples

    def _generate_single_sample(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        additional_params: Optional[Dict[str, Any]],
    ) -> str:
        """Generate a single sample."""
        strategy = get_strategy("standard")
        parameters: Dict[str, Any] = {
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if additional_params:
            parameters.update(additional_params)

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
        criteria: str,
    ) -> List[str]:
        """Rank samples using an evaluator model.

        Returns samples sorted from best to worst.
        """
        ranking_prompt = (
            f"Rank the following {len(samples)} responses to this question based on {criteria}.\n\n"
            f"Question: {original_prompt}\n\n"
        )

        for i, sample in enumerate(samples, 1):
            ranking_prompt += f"Response {i}:\n{sample}\n\n"

        ranking_prompt += (
            f"Rank these responses from best to worst. "
            f"Provide your ranking as a comma-separated list of numbers (e.g., '3,1,2' means "
            f"response 3 is best, response 1 is second, response 2 is worst).\n\n"
            f"Ranking:"
        )

        ranking_response = self._generate_single_sample(
            prompt=ranking_prompt,
            model=evaluator_model,
            temperature=0.1,  # Low temperature for consistent ranking
            max_tokens=100,
            additional_params=None,
        )

        # Parse ranking (expecting format like "3,1,2")
        try:
            ranking_str = ranking_response.strip().split("\n")[0]  # Take first line
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


class ReasoningAndVerbalizationMixin(ReasoningMixin, VerbalizationMixin):
    """Combined mixin providing both reasoning and verbalized sampling capabilities.

    Use this mixin when you want access to both sets of capabilities in a single workflow.

    Example:
        class MyWorkflow(ReasoningAndVerbalizationMixin, BaseWorkflowService):
            def my_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
                # Use reasoning with self-consistency
                samples = []
                for _ in range(5):
                    response = self.generate_with_reasoning(
                        prompt="Solve this problem...",
                        model="openrouter/deepseek/deepseek-r1",
                        temperature=0.7,
                    )
                    samples.append(response)

                # Find most common answer
                final = self.generate_with_self_consistency(...)
                return {"output": final}
    """
    pass
