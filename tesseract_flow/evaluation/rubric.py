"""LLM-powered rubric evaluator for workflow outputs."""
from __future__ import annotations

import asyncio
import json
import logging
import math
import random
from typing import Any, Dict, Iterable, Mapping, Optional

import litellm

from tesseract_flow.core.exceptions import EvaluationError
from tesseract_flow.core.types import RubricDimension

from .cache import CacheBackend, build_cache_key
from .metrics import DimensionScore, QualityScore


class RubricEvaluator:
    """Evaluate workflow output quality using a rubric and LiteLLM."""

    DEFAULT_MODEL = "anthropic/claude-3.5-sonnet"
    DEFAULT_TEMPERATURE = 0.3
    DEFAULT_RUBRIC: Dict[str, RubricDimension] = {
        "clarity": {
            "description": "Is the output clear and understandable?",
            "scale": "1-10 where 1=incomprehensible, 10=crystal clear",
        },
        "accuracy": {
            "description": "Is the output factually accurate?",
            "scale": "1-10 where 1=many errors, 10=fully accurate",
        },
        "completeness": {
            "description": "Does the output address all requirements?",
            "scale": "1-10 where 1=missing major parts, 10=comprehensive",
        },
        "usefulness": {
            "description": "Is the output actionable and useful?",
            "scale": "1-10 where 1=not useful, 10=highly actionable",
        },
    }

    def __init__(
        self,
        *,
        model: Optional[str] = None,
        temperature: float = DEFAULT_TEMPERATURE,
        logger: Optional[logging.Logger] = None,
        cache: Optional[CacheBackend] = None,
        use_cache: bool = False,
        record_cache: bool = False,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
    ) -> None:
        self._model = (model or self.DEFAULT_MODEL).strip()
        if not self._model:
            msg = "Evaluator model identifier must be non-empty."
            raise ValueError(msg)

        self._temperature = self._validate_temperature(temperature)
        self._logger = logger or logging.getLogger(__name__)
        self._cache = cache
        self._default_use_cache = bool(use_cache)
        self._default_record_cache = bool(record_cache)
        if max_retries < 1:
            msg = "max_retries must be at least 1."
            raise ValueError(msg)
        if retry_base_delay <= 0:
            msg = "retry_base_delay must be greater than zero."
            raise ValueError(msg)
        self._max_retries = max_retries
        self._retry_base_delay = retry_base_delay

    async def evaluate(
        self,
        workflow_output: str,
        rubric: Optional[Dict[str, RubricDimension]] = None,
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        extra_instructions: Optional[str] = None,
        use_cache: Optional[bool] = None,
        record_cache: Optional[bool] = None,
        cache_key: Optional[str] = None,
    ) -> QualityScore:
        """Evaluate workflow output using the provided rubric."""

        if not workflow_output or not workflow_output.strip():
            msg = "Workflow output must be a non-empty string for evaluation."
            raise EvaluationError(msg)

        rubric_definition = rubric or self.DEFAULT_RUBRIC
        selected_model = (model or self._model).strip()
        if not selected_model:
            msg = "Model identifier must be non-empty."
            raise EvaluationError(msg)
        selected_temperature = self._validate_temperature(
            temperature if temperature is not None else self._temperature
        )

        effective_use_cache = self._default_use_cache if use_cache is None else bool(use_cache)
        effective_record_cache = (
            self._default_record_cache if record_cache is None else bool(record_cache)
        )
        cache_backend = self._cache
        requested_cache = effective_use_cache or effective_record_cache or cache_key is not None
        if requested_cache and cache_backend is None:
            msg = "Caching requested but no cache backend configured."
            raise EvaluationError(msg)

        prompt = self._build_prompt(workflow_output, rubric_definition, extra_instructions)
        messages = [
            {"role": "system", "content": self._system_prompt()},
            {"role": "user", "content": prompt},
        ]

        resolved_cache_key = None
        if cache_backend is not None:
            resolved_cache_key = (cache_key or build_cache_key(prompt, selected_model, selected_temperature)).strip()
            if not resolved_cache_key:
                msg = "Cache key must be a non-empty string."
                raise EvaluationError(msg)

        cache_hit = False
        recorded_cache = False
        content: Optional[str] = None

        if cache_backend is not None and effective_use_cache:
            assert resolved_cache_key is not None
            cached = cache_backend.get(resolved_cache_key)
            if cached is not None:
                cache_hit = True
                content = cached
                self._logger.debug("Cache hit for rubric evaluation with key %s", resolved_cache_key)

        if content is None:
            response = await self._request_with_retry(
                messages=messages,
                model=selected_model,
                temperature=selected_temperature,
            )

            content = self._extract_response_content(response)

            if cache_backend is not None and effective_record_cache:
                assert resolved_cache_key is not None
                cache_backend.set(resolved_cache_key, content)
                recorded_cache = True
                self._logger.debug(
                    "Recorded rubric evaluation response to cache key %s", resolved_cache_key
                )

        assert content is not None  # for type-checkers
        parsed_payload = self._load_json(content)
        dimension_scores = self._parse_dimension_scores(parsed_payload, rubric_definition)

        quality = QualityScore(
            dimension_scores=dimension_scores,
            evaluator_model=selected_model,
        )
        metadata = {
            "rubric": rubric_definition,
            "raw_response": parsed_payload,
            "temperature": selected_temperature,
        }
        if resolved_cache_key is not None:
            metadata.update(
                {
                    "cache_key": resolved_cache_key,
                    "cache_hit": cache_hit,
                }
            )
            if recorded_cache:
                metadata["cache_recorded"] = True
        return quality.with_metadata(**metadata)

    async def _request_with_retry(
        self,
        *,
        messages: Iterable[Mapping[str, Any]],
        model: str,
        temperature: float,
    ) -> Any:
        """Call LiteLLM with exponential backoff and jitter."""

        attempt = 1
        payload = list(messages)
        last_error: Optional[Exception] = None
        while attempt <= self._max_retries:
            try:
                self._logger.debug(
                    "Rubric evaluation attempt %s/%s with model %s", attempt, self._max_retries, model
                )
                return await litellm.acompletion(
                    model=model,
                    messages=payload,
                    temperature=temperature,
                    response_format={"type": "json_object"},
                )
            except Exception as exc:  # pragma: no cover - LiteLLM errors are external
                last_error = exc
                if attempt >= self._max_retries:
                    break
                delay = self._compute_retry_delay(attempt)
                self._logger.warning(
                    "Rubric evaluation attempt %s failed (%s). Retrying in %.2fs...",
                    attempt,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
                attempt += 1

        assert last_error is not None  # for type-checkers
        self._logger.exception(
            "Rubric evaluation failed after %s attempts: %s", self._max_retries, last_error
        )
        raise EvaluationError(
            f"LLM evaluation request failed after {self._max_retries} attempts."
        ) from last_error

    def _compute_retry_delay(self, attempt: int) -> float:
        base_delay = self._retry_base_delay * (2 ** (attempt - 1))
        jitter = random.uniform(0, base_delay * 0.25)
        return base_delay + jitter

    def _build_prompt(
        self,
        workflow_output: str,
        rubric: Mapping[str, RubricDimension],
        extra_instructions: Optional[str],
    ) -> str:
        rubric_text = self._format_rubric(rubric.items())
        instructions = "\n" + extra_instructions.strip() if extra_instructions else ""
        return (
            "You are an impartial expert evaluator."
            " Assess the workflow output using the rubric."
            " Think step-by-step before scoring each dimension."
            "\n\nOUTPUT TO EVALUATE:\n" + workflow_output.strip() +
            "\n\nRUBRIC:\n" + rubric_text +
            "\nINSTRUCTIONS:\n"
            "1. Reason carefully about each dimension.\n"
            "2. Provide concise reasoning referencing the rubric.\n"
            "3. Assign a score following the specified scale.\n"
            "4. Respond ONLY in JSON with numeric scores."
            "\n\nJSON RESPONSE TEMPLATE:\n"
            "{\n"
            "  \"dimension_name\": {\n"
            "    \"score\": <number>,\n"
            "    \"reasoning\": \"<why you chose the score>\"\n"
            "  }, ...\n"
            "}"
            f"{instructions}\n"
        )

    def _system_prompt(self) -> str:
        return (
            "You are a meticulous and unbiased reviewer."
            " Provide honest assessments and avoid revealing deliberation summaries."
        )

    def _format_rubric(self, dimensions: Iterable[tuple[str, RubricDimension]]) -> str:
        lines = []
        for name, metadata in dimensions:
            lines.append(
                f"- {name}: {metadata['description']} (Scale: {metadata['scale']})"
            )
        return "\n".join(lines)

    def _extract_response_content(self, response: Any) -> str:
        choices = None
        if isinstance(response, Mapping):
            choices = response.get("choices")
        else:
            choices = getattr(response, "choices", None)

        if not choices:
            msg = "Evaluator response did not include any choices."
            raise EvaluationError(msg)

        first_choice = choices[0]
        message = (
            first_choice.get("message")
            if isinstance(first_choice, Mapping)
            else getattr(first_choice, "message", None)
        )
        if message is None:
            msg = "Evaluator response choice missing message content."
            raise EvaluationError(msg)

        content = (
            message.get("content")
            if isinstance(message, Mapping)
            else getattr(message, "content", None)
        )

        if isinstance(content, list):
            combined = "".join(part.get("text", "") for part in content if isinstance(part, Mapping))
            content = combined

        if not isinstance(content, str):
            msg = "Evaluator response content must be a string."
            raise EvaluationError(msg)
        return content

    def _load_json(self, content: str) -> Mapping[str, Any]:
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            msg = "Evaluator response was not valid JSON."
            raise EvaluationError(msg) from exc

    def _parse_dimension_scores(
        self,
        payload: Mapping[str, Any],
        rubric: Mapping[str, RubricDimension],
    ) -> Dict[str, DimensionScore]:
        scores: Dict[str, DimensionScore] = {}
        for name in rubric:
            entry = payload.get(name)
            if entry is None:
                msg = f"Evaluator response missing score for dimension '{name}'."
                raise EvaluationError(msg)
            if isinstance(entry, Mapping):
                raw_score = entry.get("score")
                reasoning = entry.get("reasoning")
            else:
                raw_score = entry
                reasoning = None
            normalized_score = self._normalize_score(raw_score)
            scores[name] = DimensionScore(score=normalized_score, reasoning=reasoning)
        return scores

    def _normalize_score(self, raw_score: Any) -> float:
        try:
            value = self._coerce_numeric(raw_score)
        except (TypeError, ValueError) as exc:
            msg = "Dimension score must be a numeric value."
            raise EvaluationError(msg) from exc

        if 0.0 <= value <= 1.0:
            return value
        if 1.0 <= value <= 10.0:
            return value / 10.0

        msg = "Dimension score must be between 0-1 or 1-10."
        raise EvaluationError(msg)

    def _coerce_numeric(self, value: Any) -> float:
        if isinstance(value, (int, float)) and math.isfinite(value):
            return float(value)
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                msg = "Dimension score string cannot be empty."
                raise ValueError(msg)
            numeric = float(stripped)
            if not math.isfinite(numeric):
                msg = "Dimension score must be finite."
                raise ValueError(msg)
            return numeric
        msg = "Unsupported score type."
        raise TypeError(msg)

    def _validate_temperature(self, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            msg = "Temperature must be between 0.0 and 1.0."
            raise ValueError(msg)
        return float(value)
