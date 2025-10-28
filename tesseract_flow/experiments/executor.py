"""Experiment execution orchestration for Taguchi L8 runs."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Sequence

from tesseract_flow.core.base_workflow import BaseWorkflowService
from tesseract_flow.core.config import (
    ExperimentConfig,
    ExperimentMetadata,
    ExperimentRun,
    TestConfiguration,
    TestResult,
)
from tesseract_flow.core.exceptions import ExperimentError, WorkflowExecutionError
from tesseract_flow.core.strategies import GENERATION_STRATEGIES
from tesseract_flow.core.types import RubricDimension
from tesseract_flow.evaluation.rubric import RubricEvaluator
from tesseract_flow.experiments.taguchi import generate_test_configs

logger = logging.getLogger(__name__)


class ExperimentExecutor:
    """Coordinate workflow execution, evaluation, and persistence for experiments."""

    def __init__(
        self,
        workflow_resolver: Callable[[str, ExperimentConfig], BaseWorkflowService],
        evaluator: RubricEvaluator,
        *,
        dependency_versions: Optional[Mapping[str, str]] = None,
        non_deterministic_sources: Optional[Sequence[str]] = None,
    ) -> None:
        self._workflow_resolver = workflow_resolver
        self._evaluator = evaluator
        self._dependency_versions = dict(dependency_versions or {})
        self._non_deterministic_sources = list(non_deterministic_sources or ["llm_sampling"])

    async def run(
        self,
        config: ExperimentConfig,
        *,
        experiment_id: Optional[str] = None,
        resume_from: Optional[ExperimentRun] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        persist_path: Optional[Path | str] = None,
        extra_instructions: Optional[str] = None,
        replications: int = 1,
    ) -> ExperimentRun:
        """Execute all test configurations defined by ``config`` sequentially.

        Args:
            config: Experiment configuration
            experiment_id: Optional custom experiment ID
            resume_from: Optional run to resume from
            progress_callback: Optional callback for progress updates
            persist_path: Optional path to persist results
            extra_instructions: Optional additional instructions for the workflow
            replications: Number of times to replicate each test configuration (default: 1)

        Returns:
            The completed experiment run
        """

        persistence_path = Path(persist_path) if persist_path is not None else None

        if resume_from is not None:
            self._validate_resume_config(config, resume_from)
            run_state = resume_from
            test_configurations = run_state.test_configurations
            experiment_identifier = run_state.experiment_id
            logger.info(
                "Resuming experiment %s with %s/%s completed tests",
                experiment_identifier,
                len(run_state.results),
                len(test_configurations),
            )
        else:
            test_configurations = generate_test_configs(config, replications=replications)
            metadata = ExperimentMetadata.from_config(
                config,
                dependencies=self._dependency_versions,
                non_deterministic_sources=self._non_deterministic_sources,
            )
            experiment_identifier = experiment_id or self._build_experiment_id(config)
            run_state = ExperimentRun(
                experiment_id=experiment_identifier,
                config=config,
                test_configurations=test_configurations,
                experiment_metadata=metadata,
            )
            logger.info(
                "Starting experiment %s with %s tests", experiment_identifier, len(test_configurations)
            )

        total_tests = len(test_configurations)
        run_state = self._ensure_running_state(run_state)

        if persistence_path is not None:
            self.save_run(run_state, persistence_path)

        if progress_callback:
            progress_callback(len(run_state.results), total_tests)

        workflow_service = self._workflow_resolver(config.workflow, config)

        try:
            for test_config in test_configurations:
                if any(result.test_number == test_config.test_number for result in run_state.results):
                    continue

                logger.debug(
                    "Running test %s/%s (test #%s)",
                    len(run_state.results) + 1,
                    total_tests,
                    test_config.test_number,
                )
                result = await self.run_single_test(
                    test_config,
                    workflow_service,
                    self._evaluator,
                    experiment_config=config,
                    rubric=config.workflow_config.rubric if config.workflow_config else None,
                    extra_instructions=extra_instructions,
                )
                run_state = run_state.record_result(result)

                if persistence_path is not None:
                    self.save_run(run_state, persistence_path)

                if progress_callback:
                    progress_callback(len(run_state.results), total_tests)

            # Only mark as completed if not already completed (handles resume of finished experiments)
            if run_state.status != "COMPLETED":
                run_state = run_state.mark_completed()
                logger.info("Experiment %s completed successfully", experiment_identifier)
            else:
                logger.info("Experiment %s was already completed", experiment_identifier)

            if persistence_path is not None:
                self.save_run(run_state, persistence_path)

            return run_state
        except Exception as exc:  # pragma: no cover - defensive guard
            error_message = str(exc).strip() or exc.__class__.__name__
            if run_state.status == "RUNNING":
                try:
                    run_state = run_state.mark_failed(error_message)
                except ValueError:
                    run_state = run_state.model_copy(update={"status": "FAILED", "error": error_message})
                if persistence_path is not None:
                    self.save_run(run_state, persistence_path)
                logger.error(
                    "Experiment %s failed after %s/%s tests: %s",
                    experiment_identifier,
                    len(run_state.results),
                    total_tests,
                    error_message,
                )

            if isinstance(exc, ExperimentError):
                raise
            raise ExperimentError("Experiment execution failed.") from exc

    async def run_single_test(
        self,
        test_config: TestConfiguration,
        workflow_service: BaseWorkflowService,
        evaluator: RubricEvaluator,
        *,
        experiment_config: Optional[ExperimentConfig] = None,
        rubric: Optional[Dict[str, RubricDimension]] = None,
        extra_instructions: Optional[str] = None,
    ) -> TestResult:
        """Execute a single test configuration and evaluate its output."""

        # Log test configuration at start
        config_str = ", ".join(f"{k}={v}" for k, v in test_config.config_values.items())
        logger.info(
            "Starting test %d: %s",
            test_config.test_number,
            config_str,
        )

        workflow_input = self._prepare_workflow_input(
            workflow_service, test_config, experiment_config
        )

        loop = asyncio.get_running_loop()
        start = perf_counter()

        try:
            workflow_output = await loop.run_in_executor(
                None, workflow_service.run, workflow_input
            )
        except WorkflowExecutionError as exc:
            # Provide context about which test failed
            error_msg = f"Workflow execution failed for test #{test_config.test_number}"
            if hasattr(exc, "__cause__") and exc.__cause__:
                error_msg += f": {type(exc.__cause__).__name__}: {exc.__cause__}"
            elif str(exc):
                error_msg += f": {exc}"
            raise ExperimentError(error_msg) from exc
        except ValueError as exc:
            # Catch configuration errors (e.g., unknown strategy)
            error_msg = f"Configuration error in test #{test_config.test_number}: {exc}"
            raise ExperimentError(error_msg) from exc
        except KeyError as exc:
            # Catch missing keys (e.g., unknown generation strategy)
            error_msg = f"Missing configuration in test #{test_config.test_number}: {exc}"
            if "strategy" in str(exc).lower():
                error_msg += f". Available strategies: {list(GENERATION_STRATEGIES.keys())}"
            raise ExperimentError(error_msg) from exc
        except Exception as exc:  # pragma: no cover - defensive guard
            error_msg = f"Unexpected error in test #{test_config.test_number}: {type(exc).__name__}: {exc}"
            raise ExperimentError(error_msg) from exc

        duration_ms = (perf_counter() - start) * 1000.0
        workflow_metadata = self._extract_workflow_metadata(workflow_service)
        if "duration_seconds" in workflow_metadata:
            duration_ms = float(workflow_metadata["duration_seconds"]) * 1000.0

        output_text = self._render_for_evaluation(workflow_output)

        # Extract calibration_examples from workflow config if present
        calibration_examples = None
        if experiment_config and experiment_config.workflow_config:
            calibration_examples = getattr(experiment_config.workflow_config, "calibration_examples", None)

        quality_score = await evaluator.evaluate(
            output_text,
            rubric=rubric,
            calibration_examples=calibration_examples,
            extra_instructions=extra_instructions,
        )

        cost = self._extract_numeric(workflow_output, workflow_metadata, ["cost", "total_cost"], default=0.0)
        latency = self._extract_numeric(
            workflow_output,
            workflow_metadata,
            ["latency_ms", "latency", "duration_ms"],
            default=duration_ms,
        )

        metadata = self._merge_metadata(workflow_output, workflow_metadata)
        evaluation_metadata = dict(quality_score.metadata)
        evaluation_metadata["model"] = quality_score.evaluator_model
        metadata.setdefault("evaluation", {}).update(evaluation_metadata)

        enriched_score = quality_score.with_metadata(**evaluation_metadata)

        logger.debug(
            "Test %s completed with quality %.2f, cost %.4f, latency %.2fms",
            test_config.test_number,
            quality_score.overall_score,
            cost,
            latency,
        )

        return TestResult(
            test_number=test_config.test_number,
            config=test_config,
            quality_score=enriched_score,
            cost=max(0.0, cost),
            latency=max(0.0, latency),
            workflow_output=output_text,
            metadata=metadata,
        )

    def save_run(self, run: ExperimentRun, path: Path | str) -> Path:
        """Persist an experiment run to disk as JSON."""

        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        serialized = run.model_dump_json(indent=2, exclude_none=True)
        file_path.write_text(serialized, encoding="utf-8")
        logger.debug("Persisted experiment run %s to %s", run.experiment_id, file_path)
        return file_path

    @staticmethod
    def load_run(path: Path | str) -> ExperimentRun:
        """Load an experiment run from a JSON file."""

        file_path = Path(path)
        data = json.loads(file_path.read_text(encoding="utf-8"))
        return ExperimentRun.model_validate(data)

    def _ensure_running_state(self, run: ExperimentRun) -> ExperimentRun:
        if run.status == "COMPLETED":
            return run
        if run.status == "RUNNING":
            return run
        return run.mark_running(started_at=run.started_at)

    def _prepare_workflow_input(
        self,
        workflow_service: BaseWorkflowService,
        test_config: TestConfiguration,
        experiment_config: Optional[ExperimentConfig],
    ) -> Any:
        if hasattr(workflow_service, "prepare_input"):
            return workflow_service.prepare_input(test_config, experiment_config)
        return test_config

    def _extract_workflow_metadata(self, workflow_service: BaseWorkflowService) -> Dict[str, Any]:
        metadata = getattr(workflow_service, "last_run_metadata", None)
        if isinstance(metadata, Mapping):
            return dict(metadata)
        return {}

    def _render_for_evaluation(self, workflow_output: Any) -> str:
        if hasattr(workflow_output, "render_for_evaluation"):
            rendered = workflow_output.render_for_evaluation()
            if isinstance(rendered, str):
                return rendered.strip()
        if hasattr(workflow_output, "evaluation_text"):
            value = getattr(workflow_output, "evaluation_text")
            if isinstance(value, str):
                return value.strip()
        if hasattr(workflow_output, "model_dump"):
            data = workflow_output.model_dump(mode="python")  # type: ignore[attr-defined]
            for key in ("evaluation_text", "content", "output", "review"):
                value = data.get(key)
                if isinstance(value, str):
                    return value.strip()
        if isinstance(workflow_output, Mapping):
            for key in ("evaluation_text", "content", "output", "review"):
                value = workflow_output.get(key)
                if isinstance(value, str):
                    return value.strip()
        return str(workflow_output).strip()

    def _extract_numeric(
        self,
        workflow_output: Any,
        workflow_metadata: Mapping[str, Any],
        keys: Iterable[str],
        *,
        default: float,
    ) -> float:
        for key in keys:
            if hasattr(workflow_output, key):
                value = getattr(workflow_output, key)
                numeric = self._coerce_float(value)
                if numeric is not None:
                    return numeric
            if hasattr(workflow_output, "model_dump"):
                data = workflow_output.model_dump(mode="python")  # type: ignore[attr-defined]
                if key in data:
                    numeric = self._coerce_float(data[key])
                    if numeric is not None:
                        return numeric
            if key in workflow_metadata:
                numeric = self._coerce_float(workflow_metadata[key])
                if numeric is not None:
                    return numeric
        return default

    def _merge_metadata(self, workflow_output: Any, workflow_metadata: Mapping[str, Any]) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {}
        if hasattr(workflow_output, "metadata"):
            candidate = getattr(workflow_output, "metadata")
            if isinstance(candidate, Mapping):
                metadata.update(candidate)
        elif hasattr(workflow_output, "model_dump"):
            data = workflow_output.model_dump(mode="python")  # type: ignore[attr-defined]
            candidate = data.get("metadata")
            if isinstance(candidate, Mapping):
                metadata.update(candidate)
        metadata.setdefault("workflow", {}).update(dict(workflow_metadata))
        return metadata

    def _coerce_float(self, value: Any) -> Optional[float]:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        if not (numeric == numeric):  # NaN check
            return None
        return numeric

    def _build_experiment_id(self, config: ExperimentConfig) -> str:
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%S")
        sanitized = config.name.strip().replace(" ", "_")
        return f"{sanitized or 'experiment'}-{timestamp}"

    def _validate_resume_config(self, config: ExperimentConfig, run: ExperimentRun) -> None:
        new_payload = config.model_dump(mode="json")
        existing_payload = run.config.model_dump(mode="json")
        if new_payload != existing_payload:
            raise ExperimentError(
                "Cannot resume experiment: configuration differs from saved state."
            )


__all__ = ["ExperimentExecutor"]

