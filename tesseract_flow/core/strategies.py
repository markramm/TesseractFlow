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
        response = await litellm.acompletion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            **parameters,
        )
        choices = response.get("choices", [])
        if not choices:
            return ""
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if isinstance(content, list):  # LiteLLM may return content blocks
            content = "".join(str(block) for block in content)
        return str(content).strip()


GENERATION_STRATEGIES: Dict[str, GenerationStrategy] = {
    "standard": StandardStrategy(),
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
