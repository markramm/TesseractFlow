"""Tests for reasoning and verbalized sampling mixins."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tesseract_flow.core.mixins import (
    ReasoningAndVerbalizationMixin,
    ReasoningMixin,
    VerbalizationMixin,
)


class TestReasoningMixin:
    """Tests for ReasoningMixin."""

    @pytest.fixture
    def mixin_instance(self):
        """Create a minimal instance with ReasoningMixin."""
        return ReasoningMixin()

    def test_generate_with_reasoning_r1_model(self, mixin_instance):
        """Test reasoning generation with DeepSeek R1 model."""
        with patch("tesseract_flow.core.mixins.get_strategy") as mock_get_strategy:
            mock_strategy = AsyncMock()
            mock_strategy.generate = AsyncMock(return_value="Test response")
            mock_get_strategy.return_value = mock_strategy

            result = mixin_instance.generate_with_reasoning(
                prompt="Solve this problem",
                model="openrouter/deepseek/deepseek-r1",
                temperature=0.3,
            )

            assert result == "Test response"
            # Verify reasoning_mode parameter was passed for R1
            call_args = mock_strategy.generate.call_args
            assert call_args.kwargs["config"]["reasoning_mode"] == "native_r1"

    def test_generate_with_reasoning_v32_model(self, mixin_instance):
        """Test reasoning generation with DeepSeek V3.2 model."""
        with patch("tesseract_flow.core.mixins.get_strategy") as mock_get_strategy:
            mock_strategy = AsyncMock()
            mock_strategy.generate = AsyncMock(return_value="Test response")
            mock_get_strategy.return_value = mock_strategy

            result = mixin_instance.generate_with_reasoning(
                prompt="Solve this problem",
                model="openrouter/deepseek/deepseek-v3.2-exp",
                temperature=0.3,
            )

            assert result == "Test response"
            # Verify reasoning.enabled parameter was passed for V3.2
            call_args = mock_strategy.generate.call_args
            assert call_args.kwargs["config"]["reasoning.enabled"] is True

    def test_generate_with_reasoning_other_model(self, mixin_instance):
        """Test reasoning falls back to CoT prompting for non-DeepSeek models."""
        with patch("tesseract_flow.core.mixins.get_strategy") as mock_get_strategy:
            mock_strategy = AsyncMock()
            mock_strategy.generate = AsyncMock(return_value="Test response")
            mock_get_strategy.return_value = mock_strategy

            result = mixin_instance.generate_with_reasoning(
                prompt="Solve this problem",
                model="openrouter/anthropic/claude-haiku-4.5",
                temperature=0.3,
                reasoning_visibility="visible",
            )

            assert result == "Test response"
            # Verify CoT prompt was prepended
            call_args = mock_strategy.generate.call_args
            prompt_used = call_args.args[0]
            assert "Think step-by-step" in prompt_used

    def test_parse_reasoning_and_solution_with_marker(self, mixin_instance):
        """Test parsing response with clear Answer: marker."""
        response = "First, let's analyze. Second, check assumptions. Answer: The answer is 42."

        reasoning, solution = mixin_instance.parse_reasoning_and_solution(response)

        assert reasoning == "First, let's analyze. Second, check assumptions."
        assert solution == "The answer is 42."

    def test_parse_reasoning_and_solution_without_marker(self, mixin_instance):
        """Test parsing response without clear marker."""
        response = "This is a complete response without markers"

        reasoning, solution = mixin_instance.parse_reasoning_and_solution(response)

        # Both should be the same when no marker is found
        assert reasoning == response
        assert solution == response


class TestVerbalizationMixin:
    """Tests for VerbalizationMixin."""

    @pytest.fixture
    def mixin_instance(self):
        """Create a minimal instance with VerbalizationMixin."""
        return VerbalizationMixin()

    def test_generate_with_self_consistency(self, mixin_instance):
        """Test self-consistency sampling returns most common answer."""
        with patch.object(mixin_instance, "_generate_multiple_samples") as mock_gen:
            # Mock 5 samples with 3 saying "42" and 2 saying "41"
            mock_gen.return_value = [
                "The answer is 42.",
                "I think it's 41.",
                "The answer is 42.",
                "The answer is 42.",
                "It should be 41.",
            ]

            with patch.object(mixin_instance, "_extract_final_answer") as mock_extract:
                # Mock extraction to return consistent answers
                mock_extract.side_effect = ["42", "41", "42", "42", "41"]

                result = mixin_instance.generate_with_self_consistency(
                    prompt="What is 2+2?",
                    model="openrouter/anthropic/claude-haiku-4.5",
                    n_samples=5,
                )

                # Should return most common answer
                assert result == "42"

    def test_generate_with_sample_and_rank(self, mixin_instance):
        """Test sample-and-rank returns highest-ranked sample."""
        with patch.object(mixin_instance, "_generate_multiple_samples") as mock_gen:
            mock_samples = ["Response A", "Response B", "Response C"]
            mock_gen.return_value = mock_samples

            with patch.object(mixin_instance, "_rank_samples") as mock_rank:
                # Mock ranking to return samples in reverse order
                mock_rank.return_value = ["Response C", "Response B", "Response A"]

                result = mixin_instance.generate_with_sample_and_rank(
                    prompt="Test prompt",
                    model="openrouter/anthropic/claude-haiku-4.5",
                    evaluator_model="openrouter/anthropic/claude-haiku-4.5",
                    n_samples=3,
                )

                # Should return first in ranked list
                assert result == "Response C"

    def test_generate_with_ensemble(self, mixin_instance):
        """Test ensemble generation synthesizes multiple approaches."""
        with patch.object(mixin_instance, "_generate_single_sample") as mock_gen:
            # First 3 calls are for different approaches, 4th is synthesis
            mock_gen.side_effect = [
                "Analytical response",
                "Creative response",
                "Methodical response",
                "Final synthesized answer",
            ]

            result = mixin_instance.generate_with_ensemble(
                prompt="Test prompt",
                model="openrouter/anthropic/claude-haiku-4.5",
            )

            # Should return the synthesized response
            assert result == "Final synthesized answer"
            # Should have been called 4 times (3 approaches + 1 synthesis)
            assert mock_gen.call_count == 4

    def test_extract_final_answer_with_marker(self, mixin_instance):
        """Test extraction of final answer with Answer: marker."""
        text = "Let's think through this. Answer: The final answer is 42."

        answer = mixin_instance._extract_final_answer(text)

        assert answer == "The final answer is 42"

    def test_extract_final_answer_without_marker(self, mixin_instance):
        """Test extraction falls back to last sentence when no marker."""
        text = "First sentence. Second sentence. Final sentence."

        answer = mixin_instance._extract_final_answer(text)

        # Should return the last sentence
        assert answer == "Final sentence"


class TestReasoningAndVerbalizationMixin:
    """Tests for combined ReasoningAndVerbalizationMixin."""

    @pytest.fixture
    def mixin_instance(self):
        """Create instance with both mixins."""
        return ReasoningAndVerbalizationMixin()

    def test_has_both_capabilities(self, mixin_instance):
        """Test that combined mixin has both reasoning and verbalization methods."""
        # Should have reasoning methods
        assert hasattr(mixin_instance, "generate_with_reasoning")
        assert hasattr(mixin_instance, "parse_reasoning_and_solution")

        # Should have verbalization methods
        assert hasattr(mixin_instance, "generate_with_self_consistency")
        assert hasattr(mixin_instance, "generate_with_sample_and_rank")
        assert hasattr(mixin_instance, "generate_with_ensemble")

    def test_can_use_both_reasoning_and_verbalization(self, mixin_instance):
        """Test that both reasoning and verbalization work together."""
        with patch("tesseract_flow.core.mixins.get_strategy") as mock_get_strategy:
            mock_strategy = AsyncMock()
            mock_strategy.generate = AsyncMock(return_value="42")
            mock_get_strategy.return_value = mock_strategy

            # Test reasoning
            result1 = mixin_instance.generate_with_reasoning(
                prompt="Test",
                model="openrouter/deepseek/deepseek-r1",
            )
            assert result1 == "42"

            # Test verbalization (mock the internal methods)
            with patch.object(mixin_instance, "_generate_multiple_samples") as mock_gen:
                mock_gen.return_value = ["42", "42", "42"]
                with patch.object(mixin_instance, "_extract_final_answer") as mock_extract:
                    mock_extract.return_value = "42"

                    result2 = mixin_instance.generate_with_self_consistency(
                        prompt="Test",
                        model="openrouter/anthropic/claude-haiku-4.5",
                        n_samples=3,
                    )
                    assert result2 == "42"
