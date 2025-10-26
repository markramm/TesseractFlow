import asyncio
from typing import Any

import pytest

from tesseract_flow.core.strategies import (
    GENERATION_STRATEGIES,
    StandardStrategy,
    GenerationStrategy,
    get_strategy,
    register_strategy,
)


def test_standard_strategy_uses_litellm(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_args: dict[str, Any] = {}

    async def fake_completion(**kwargs: Any) -> dict[str, Any]:
        captured_args.update(kwargs)
        return {"choices": [{"message": {"content": " result "}}]}

    monkeypatch.setattr(
        "tesseract_flow.core.strategies.litellm.acompletion", fake_completion, raising=False
    )

    strategy = StandardStrategy()
    result = asyncio.run(
        strategy.generate("Prompt", model="test-model", config={"temperature": 0.5})
    )
    assert result == "result"
    assert captured_args["temperature"] == 0.5
    assert captured_args["model"] == "test-model"


def test_standard_strategy_returns_empty_string(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_completion(**kwargs: Any) -> dict[str, Any]:
        return {"choices": []}

    monkeypatch.setattr(
        "tesseract_flow.core.strategies.litellm.acompletion", fake_completion, raising=False
    )

    strategy = StandardStrategy()
    result = asyncio.run(strategy.generate("Prompt", model="test-model"))
    assert result == ""


def test_standard_strategy_flattens_list_content(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_completion(**kwargs: Any) -> dict[str, Any]:
        return {"choices": [{"message": {"content": [" part1", " part2 "]}}]}

    monkeypatch.setattr(
        "tesseract_flow.core.strategies.litellm.acompletion", fake_completion, raising=False
    )

    strategy = StandardStrategy()
    result = asyncio.run(strategy.generate("Prompt", model="test-model"))
    assert result == "part1 part2"


def test_get_strategy_returns_registered_strategy() -> None:
    strategy = get_strategy("standard")
    assert isinstance(strategy, GenerationStrategy)


def test_register_strategy_adds_new_strategy() -> None:
    class DummyStrategy:
        async def generate(self, prompt: str, *, model: str, config: dict[str, Any] | None = None) -> str:
            return f"{model}:{prompt}"

    register_strategy("dummy", DummyStrategy())
    try:
        strategy = get_strategy("dummy")
        assert isinstance(strategy, DummyStrategy)
        assert asyncio.run(strategy.generate("hello", model="model")) == "model:hello"
    finally:
        GENERATION_STRATEGIES.pop("dummy", None)


def test_get_strategy_unknown_name_raises() -> None:
    with pytest.raises(ValueError):
        get_strategy("missing")
