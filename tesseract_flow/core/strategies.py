"""Generation strategy protocol and registry."""
from __future__ import annotations

from typing import Any, Dict, Mapping, Protocol, runtime_checkable

import litellm


@runtime_checkable
class GenerationStrategy(Protocol):
    """Protocol for workflow generation strategies."""

    async def generate(
        self,
        prompt: str,
        *,
        model: str,
        config: Mapping[str, Any] | None = None,
    ) -> str:
        """Generate text for the given prompt using provided model settings."""


class StandardStrategy:
    """Default generation strategy using LiteLLM completion API."""

    async def generate(
        self,
        prompt: str,
        *,
        model: str,
        config: Mapping[str, Any] | None = None,
    ) -> str:
        parameters: Dict[str, Any] = {}
        if config is not None:
            parameters.update(config)
        temperature = parameters.pop("temperature", 0.0)

        try:
            response = await litellm.acompletion(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                **parameters,
            )
        except litellm.BadRequestError as exc:
            raise ValueError(f"Invalid model or request for '{model}': {exc}") from exc
        except litellm.AuthenticationError as exc:
            raise ValueError(f"Authentication failed for model '{model}': {exc}") from exc
        except litellm.RateLimitError as exc:
            raise ValueError(f"Rate limit exceeded for model '{model}': {exc}") from exc
        except Exception as exc:
            # Preserve other LiteLLM errors with context
            raise ValueError(f"LLM API call failed for model '{model}': {type(exc).__name__}: {exc}") from exc

        choices = response.get("choices", [])
        if not choices:
            return ""
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if isinstance(content, list):  # LiteLLM may return content blocks
            content = "".join(str(block) for block in content)
        return str(content).strip()


class ChainOfThoughtStrategy:
    """Chain-of-thought prompting strategy for step-by-step reasoning."""

    async def generate(
        self,
        prompt: str,
        *,
        model: str,
        config: Mapping[str, Any] | None = None,
    ) -> str:
        parameters: Dict[str, Any] = {}
        if config is not None:
            parameters.update(config)
        temperature = parameters.pop("temperature", 0.0)

        # Prepend chain-of-thought instruction
        cot_prompt = (
            "Think step-by-step and explain your reasoning before providing the final answer.\n\n"
            f"{prompt}"
        )

        try:
            response = await litellm.acompletion(
                model=model,
                messages=[{"role": "user", "content": cot_prompt}],
                temperature=temperature,
                **parameters,
            )
        except litellm.BadRequestError as exc:
            raise ValueError(f"Invalid model or request for '{model}': {exc}") from exc
        except litellm.AuthenticationError as exc:
            raise ValueError(f"Authentication failed for model '{model}': {exc}") from exc
        except litellm.RateLimitError as exc:
            raise ValueError(f"Rate limit exceeded for model '{model}': {exc}") from exc
        except Exception as exc:
            # Preserve other LiteLLM errors with context
            raise ValueError(f"LLM API call failed for model '{model}': {type(exc).__name__}: {exc}") from exc

        choices = response.get("choices", [])
        if not choices:
            return ""
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if isinstance(content, list):
            content = "".join(str(block) for block in content)
        return str(content).strip()


class FewShotStrategy:
    """Few-shot prompting strategy with examples."""

    def __init__(self, examples: list[tuple[str, str]] | None = None):
        """Initialize with optional example pairs of (input, output)."""
        self.examples = examples or []

    async def generate(
        self,
        prompt: str,
        *,
        model: str,
        config: Mapping[str, Any] | None = None,
    ) -> str:
        parameters: Dict[str, Any] = {}
        if config is not None:
            parameters.update(config)
        temperature = parameters.pop("temperature", 0.0)

        # Build messages with examples
        messages = []
        for example_input, example_output in self.examples:
            messages.append({"role": "user", "content": example_input})
            messages.append({"role": "assistant", "content": example_output})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await litellm.acompletion(
                model=model,
                messages=messages,
                temperature=temperature,
                **parameters,
            )
        except litellm.BadRequestError as exc:
            raise ValueError(f"Invalid model or request for '{model}': {exc}") from exc
        except litellm.AuthenticationError as exc:
            raise ValueError(f"Authentication failed for model '{model}': {exc}") from exc
        except litellm.RateLimitError as exc:
            raise ValueError(f"Rate limit exceeded for model '{model}': {exc}") from exc
        except Exception as exc:
            # Preserve other LiteLLM errors with context
            raise ValueError(f"LLM API call failed for model '{model}': {type(exc).__name__}: {exc}") from exc

        choices = response.get("choices", [])
        if not choices:
            return ""
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if isinstance(content, list):
            content = "".join(str(block) for block in content)
        return str(content).strip()


GENERATION_STRATEGIES: Dict[str, GenerationStrategy] = {
    "standard": StandardStrategy(),
    "chain_of_thought": ChainOfThoughtStrategy(),
    "few_shot": FewShotStrategy(),
}


def get_strategy(name: str) -> GenerationStrategy:
    """Retrieve a generation strategy by name."""

    try:
        return GENERATION_STRATEGIES[name]
    except KeyError as exc:  # pragma: no cover - defensive guard
        raise ValueError(f"Unknown generation strategy: {name}") from exc


def register_strategy(name: str, strategy: GenerationStrategy) -> None:
    """Register a custom generation strategy."""

    GENERATION_STRATEGIES[name] = strategy
