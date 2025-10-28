"""Core configuration models for experiments and workflows."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)

from tesseract_flow.core.exceptions import ConfigurationError

from tesseract_flow.evaluation.metrics import QualityScore
from tesseract_flow.optimization.utility import UtilityFunction

from .types import ExperimentStatus, RubricDimension, UtilityWeights as UtilityWeightsBase


class Variable(BaseModel):
    """Represents a single experimental variable with two discrete levels."""

    name: str = Field(..., min_length=1)
    level_1: Any
    level_2: Any

    model_config = ConfigDict(frozen=True)

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        if not value:
            msg = "Variable name must be non-empty."
            raise ValueError(msg)
        if value.strip() != value:
            msg = "Variable name must not contain leading or trailing whitespace."
            raise ValueError(msg)
        if value.startswith("_"):
            msg = "Variable name must not start with an underscore."
            raise ValueError(msg)
        if not value.replace("_", "").isalnum():
            msg = "Variable name must contain only alphanumeric characters and underscores."
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def _validate_levels(self) -> "Variable":
        if self.level_1 == self.level_2:
            msg = "Variable levels must be distinct."
            raise ValueError(msg)
        if type(self.level_1) is not type(self.level_2):
            msg = "Variable levels must share the same type."
            raise ValueError(msg)
        return self


class UtilityWeights(UtilityWeightsBase):
    """Utility weight configuration with additional validation."""

    @model_validator(mode="after")
    def _ensure_positive_total(self) -> "UtilityWeights":
        if self.quality == 0.0 and self.cost == 0.0 and self.time == 0.0:
            msg = "At least one utility weight must be greater than zero."
            raise ValueError(msg)
        return self


class WorkflowConfig(BaseModel):
    """Workflow-specific configuration details."""

    rubric: Dict[str, RubricDimension] = Field(default_factory=dict)
    sample_code_path: Optional[str] = None
    evaluator_model: Optional[str] = None

    model_config = ConfigDict(extra="allow")

    @field_validator("sample_code_path")
    @classmethod
    def _validate_sample_code_path(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            msg = "sample_code_path must not be empty if provided."
            raise ValueError(msg)
        return stripped


class ExperimentConfig(BaseModel):
    """Configuration for executing a Taguchi L8 experiment."""

    name: str
    workflow: str
    variables: List[Variable]
    utility_weights: UtilityWeights = Field(default_factory=UtilityWeights)
    workflow_config: WorkflowConfig | Dict[str, Any] = Field(default_factory=WorkflowConfig)
    seed: Optional[int] = Field(default=None, ge=0)

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("name", "workflow")
    @classmethod
    def _validate_identifier(cls, value: str) -> str:
        if not value:
            msg = "Experiment identifiers must be non-empty."
            raise ValueError(msg)
        if value.strip() != value:
            msg = "Experiment identifiers cannot contain leading or trailing whitespace."
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def _validate_variables(self) -> "ExperimentConfig":
        count = len(self.variables)
        if count < 4 or count > 7:
            msg = "ExperimentConfig requires between 4 and 7 variables."
            raise ValueError(msg)

        names = [variable.name for variable in self.variables]
        if len(set(names)) != count:
            msg = "Variable names must be unique within an experiment."
            raise ValueError(msg)
        return self

    @model_validator(mode="before")
    @classmethod
    def _coerce_workflow_config(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        workflow_config = data.get("workflow_config")
        if workflow_config is None:
            data["workflow_config"] = WorkflowConfig()
        elif not isinstance(workflow_config, WorkflowConfig):
            data["workflow_config"] = WorkflowConfig.model_validate(workflow_config)
        return data

    @classmethod
    def from_yaml(cls, path: Path | str) -> "ExperimentConfig":
        """Load an experiment configuration from a YAML file."""

        file_path = Path(path)
        try:
            text = file_path.read_text(encoding="utf-8")
        except OSError:
            # Surface file issues to caller for contextual handling.
            raise

        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            details = [_format_yaml_error(exc)] if str(exc).strip() else []
            message = f"Failed to parse experiment YAML at {file_path}."
            raise ConfigurationError(message, details=details) from exc

        if not isinstance(data, dict):
            message = (
                f"Experiment configuration in {file_path} must be a mapping of keys to values."
            )
            raise ConfigurationError(message)

        try:
            return cls.model_validate(data)
        except ValidationError as exc:
            message = f"Experiment configuration in {file_path} is invalid."
            raise ConfigurationError(message, details=_format_validation_errors(exc)) from exc

    def to_yaml(self, path: Path | str) -> Path:
        """Persist the configuration to a YAML file."""

        file_path = Path(path)
        with file_path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(self.model_dump(mode="json"), handle, sort_keys=False)
        return file_path


class ExperimentMetadata(BaseModel):
    """Metadata describing experiment reproducibility context."""

    config_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    dependencies: Dict[str, str] = Field(default_factory=dict)
    non_deterministic_sources: List[str] = Field(default_factory=list)
    seed: Optional[int] = None

    model_config = ConfigDict(frozen=True)

    @field_validator("config_hash")
    @classmethod
    def _validate_config_hash(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "config_hash must be a non-empty string."
            raise ValueError(msg)
        return stripped

    @model_validator(mode="before")
    @classmethod
    def _coerce_dependencies(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        dependencies = data.get("dependencies") or {}
        if not isinstance(dependencies, Mapping):
            msg = "dependencies must be provided as a mapping of package names to versions."
            raise ValueError(msg)
        data["dependencies"] = {str(name): str(version) for name, version in dependencies.items()}

        sources = data.get("non_deterministic_sources") or []
        if not isinstance(sources, Sequence) or isinstance(sources, (str, bytes)):
            msg = "non_deterministic_sources must be a sequence of strings."
            raise ValueError(msg)
        normalized_sources = sorted({str(source).strip() for source in sources if str(source).strip()})
        data["non_deterministic_sources"] = normalized_sources
        return data

    @classmethod
    def from_config(
        cls,
        config: "ExperimentConfig",
        *,
        dependencies: Optional[Mapping[str, str]] = None,
        non_deterministic_sources: Optional[Sequence[str]] = None,
    ) -> "ExperimentMetadata":
        """Create metadata derived from an :class:`ExperimentConfig`."""

        payload = config.model_dump(mode="json")
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        config_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        detected_dependencies = {
            str(name): str(version)
            for name, version in (dependencies or {}).items()
            if str(name).strip() and str(version).strip()
        }

        if not detected_dependencies:
            detected_dependencies = cls._default_dependency_versions()

        sources = list(non_deterministic_sources or ["llm_sampling"])
        return cls(
            config_hash=config_hash,
            dependencies=detected_dependencies,
            non_deterministic_sources=sources,
            seed=config.seed,
        )

    @staticmethod
    def _default_dependency_versions() -> Dict[str, str]:
        packages = ("pydantic", "langgraph", "litellm")
        versions: Dict[str, str] = {}
        for package in packages:
            try:
                versions[package] = importlib_metadata.version(package)
            except importlib_metadata.PackageNotFoundError:  # pragma: no cover - optional deps
                continue
        return versions


class TestConfiguration(BaseModel):
    """Represents a single test generated from the Taguchi L8 array.

    Note: test_number can exceed 8 when using replications (n > 1).
    With replications, the same 8 L8 configurations are repeated multiple times.
    """

    test_number: int = Field(..., ge=1)
    config_values: Dict[str, Any]
    workflow: str

    model_config = ConfigDict(frozen=True)

    @field_validator("workflow")
    @classmethod
    def _validate_workflow(cls, value: str) -> str:
        if not value:
            msg = "Workflow identifier must be non-empty."
            raise ValueError(msg)
        if value.strip() != value:
            msg = "Workflow identifier cannot contain leading or trailing whitespace."
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def _validate_values(self, info: ValidationInfo) -> "TestConfiguration":
        variable_levels = (info.context or {}).get("variable_levels")
        if not variable_levels:
            return self

        expected_names = set(variable_levels)
        provided_names = set(self.config_values)
        if provided_names != expected_names:
            missing = expected_names - provided_names
            extra = provided_names - expected_names
            details = []
            if missing:
                details.append(f"missing {sorted(missing)}")
            if extra:
                details.append(f"unexpected {sorted(extra)}")
            detail_msg = ", ".join(details)
            msg = f"Config values must match experiment variables ({detail_msg})."
            raise ValueError(msg)

        for name, value in self.config_values.items():
            allowed_values = variable_levels[name]
            if value not in allowed_values:
                msg = (
                    f"Config value for variable '{name}' must be one of the defined levels."
                )
                raise ValueError(msg)

        return self


class TestResult(BaseModel):
    """Result from executing a single test configuration.

    Note: test_number can exceed 8 when using replications (n > 1).
    With replications, the same 8 L8 configurations are repeated multiple times.
    """

    test_number: int = Field(..., ge=1)
    config: TestConfiguration
    quality_score: QualityScore
    cost: float = Field(..., ge=0.0)
    latency: float = Field(..., ge=0.0)
    utility: float = 0.0
    workflow_output: str = Field(default="")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("workflow_output")
    @classmethod
    def _normalize_output(cls, value: str) -> str:
        return value.strip()

    def with_utility(self, utility: float) -> "TestResult":
        """Return a copy of the result with an updated utility score."""

        return self.model_copy(update={"utility": utility})

    def with_metadata(self, **metadata: Any) -> "TestResult":
        """Return a copy of the result with merged metadata."""

        merged = {**self.metadata, **metadata}
        return self.model_copy(update={"metadata": merged})


class ExperimentRun(BaseModel):
    """Tracks execution progress and results for a Taguchi L8 experiment."""

    experiment_id: str
    config: ExperimentConfig
    test_configurations: List[TestConfiguration]
    results: List[TestResult] = Field(default_factory=list)
    status: ExperimentStatus = "PENDING"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    experiment_metadata: Optional[ExperimentMetadata] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    baseline_test_number: int = Field(default=1, ge=1)
    baseline_config: Optional[TestConfiguration] = None
    baseline_result: Optional[TestResult] = None
    baseline_quality: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    quality_improvement_pct: Optional[float] = None

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("experiment_id")
    @classmethod
    def _validate_experiment_id(cls, value: str) -> str:
        if not value:
            msg = "experiment_id must be non-empty."
            raise ValueError(msg)
        stripped = value.strip()
        if stripped != value:
            msg = "experiment_id cannot contain leading or trailing whitespace."
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def _validate_state(self) -> "ExperimentRun":
        num_configs = len(self.test_configurations)
        if num_configs < 8 or num_configs % 8 != 0:
            msg = (
                f"L8 experiment requires exactly 8 test configurations or a multiple of 8 "
                f"(for replications). Got {num_configs} configurations."
            )
            raise ValueError(msg)

        test_numbers = [config.test_number for config in self.test_configurations]
        if len(set(test_numbers)) != len(test_numbers):
            msg = "Test configuration numbers must be unique."
            raise ValueError(msg)

        if len(self.results) > len(self.test_configurations):
            msg = "Result count cannot exceed generated test configurations."
            raise ValueError(msg)

        if self.status == "PENDING":
            if self.results:
                msg = "Pending experiments cannot contain results."
                raise ValueError(msg)
            if self.started_at is not None:
                msg = "Pending experiments cannot define a start timestamp."
                raise ValueError(msg)
            if self.completed_at is not None:
                msg = "Pending experiments cannot define a completion timestamp."
                raise ValueError(msg)
            if self.error is not None:
                msg = "Pending experiments cannot contain errors."
                raise ValueError(msg)

        if self.status == "RUNNING":
            if not 0 <= len(self.results) <= len(self.test_configurations):
                msg = "Running experiments cannot store more results than test configurations."
                raise ValueError(msg)
            if self.completed_at is not None:
                msg = "Running experiments cannot define a completion timestamp."
                raise ValueError(msg)
            if self.error is not None:
                msg = "Running experiments cannot define an error."
                raise ValueError(msg)
            if self.started_at is None:
                msg = "Running experiments must define a start timestamp."
                raise ValueError(msg)

        if self.status == "COMPLETED":
            if len(self.results) != len(self.test_configurations):
                msg = "Completed experiments must contain results for all configurations."
                raise ValueError(msg)
            if self.completed_at is None:
                msg = "Completed experiments must define a completion timestamp."
                raise ValueError(msg)
            if self.error is not None:
                msg = "Completed experiments cannot contain an error."
                raise ValueError(msg)
            if self.started_at is None:
                msg = "Completed experiments must define a start timestamp."
                raise ValueError(msg)

        if self.status == "FAILED":
            if self.error is None:
                msg = "Failed experiments must include an error message."
                raise ValueError(msg)
            if self.started_at is None:
                msg = "Failed experiments must define a start timestamp."
                raise ValueError(msg)

        first_config = min(self.test_configurations, key=lambda item: item.test_number)

        if self.baseline_test_number != first_config.test_number:
            object.__setattr__(self, "baseline_test_number", first_config.test_number)

        if self.baseline_config is None or self.baseline_config.test_number != first_config.test_number:
            object.__setattr__(self, "baseline_config", first_config)

        if self.baseline_result is not None and self.baseline_result.test_number != first_config.test_number:
            object.__setattr__(self, "baseline_result", None)
            object.__setattr__(self, "baseline_quality", None)

        return self

    def mark_running(self, *, started_at: Optional[datetime] = None) -> "ExperimentRun":
        """Transition the experiment to RUNNING state."""

        if self.status not in {"PENDING", "FAILED"}:
            msg = "Experiment can only transition to RUNNING from PENDING or FAILED."
            raise ValueError(msg)

        timestamp = started_at or datetime.now(tz=timezone.utc)
        return self.model_copy(
            update={"status": "RUNNING", "started_at": timestamp, "error": None}
        )

    def mark_failed(self, error: str) -> "ExperimentRun":
        """Transition the experiment to FAILED state."""

        if self.status != "RUNNING":
            msg = "Failed state can only be set from RUNNING."
            raise ValueError(msg)
        stripped = error.strip()
        if not stripped:
            msg = "Error message must be non-empty."
            raise ValueError(msg)

        return self.model_copy(update={"status": "FAILED", "error": stripped})

    def mark_completed(self, *, completed_at: Optional[datetime] = None) -> "ExperimentRun":
        """Transition the experiment to COMPLETED state."""

        if self.status != "RUNNING":
            msg = "Experiment must be RUNNING before completion."
            raise ValueError(msg)
        if len(self.results) != len(self.test_configurations):
            msg = "Cannot complete experiment until all results are recorded."
            raise ValueError(msg)

        timestamp = completed_at or datetime.now(tz=timezone.utc)
        baseline_result = self.baseline_result
        if baseline_result is None:
            baseline_result = next(
                (item for item in self.results if item.test_number == self.baseline_test_number),
                None,
            )
        baseline_quality = (
            baseline_result.quality_score.overall_score if baseline_result else self.baseline_quality
        )
        improvement = self._calculate_improvement(self.results, baseline_quality)

        return self.model_copy(
            update={
                "status": "COMPLETED",
                "completed_at": timestamp,
                "baseline_result": baseline_result,
                "baseline_quality": baseline_quality,
                "quality_improvement_pct": improvement,
            }
        )

    def record_result(self, result: TestResult) -> "ExperimentRun":
        """Record a new test result and recalculate utilities."""

        if self.status != "RUNNING":
            msg = "Results can only be recorded while experiment is RUNNING."
            raise ValueError(msg)

        if any(existing.test_number == result.test_number for existing in self.results):
            msg = "Result for this test number has already been recorded."
            raise ValueError(msg)

        if len(self.results) >= len(self.test_configurations):
            msg = "All test results have already been recorded."
            raise ValueError(msg)

        updated_results = [*self.results, result]
        recalculated_results, metadata = self._recalculate_utilities(updated_results)

        baseline_result = self.baseline_result
        if baseline_result is None or result.test_number == self.baseline_test_number:
            baseline_result = next(
                (item for item in recalculated_results if item.test_number == self.baseline_test_number),
                None,
            )

        baseline_quality = (
            baseline_result.quality_score.overall_score if baseline_result else self.baseline_quality
        )
        improvement = self._calculate_improvement(recalculated_results, baseline_quality)

        updates = {
            "results": recalculated_results,
            "metadata": metadata,
            "baseline_result": baseline_result,
            "baseline_quality": baseline_quality,
            "quality_improvement_pct": improvement,
        }
        return self.model_copy(update=updates)

    def _recalculate_utilities(
        self, results: Iterable[TestResult]
    ) -> tuple[List[TestResult], Dict[str, Any]]:
        results_list = sorted(results, key=lambda item: item.test_number)
        if not results_list:
            return results_list, self.metadata

        utility_fn = UtilityFunction(self.config.utility_weights)
        costs = [result.cost for result in results_list]
        latencies = [result.latency for result in results_list]
        normalized_costs, cost_stats = UtilityFunction.normalize_metrics(costs)
        normalized_latencies, latency_stats = UtilityFunction.normalize_metrics(latencies)

        updated_results = []
        for result, normalized_cost, normalized_latency in zip(
            results_list, normalized_costs, normalized_latencies
        ):
            utility = utility_fn.compute(
                quality=result.quality_score.overall_score,
                cost=normalized_cost,
                latency=normalized_latency,
            )
            updated_results.append(result.with_utility(utility))

        metadata = {
            **self.metadata,
            "normalization": {
                "cost": cost_stats,
                "latency": latency_stats,
            },
        }
        return updated_results, metadata

    @staticmethod
    def _calculate_improvement(
        results: Sequence[TestResult], baseline_quality: Optional[float]
    ) -> Optional[float]:
        if baseline_quality is None or baseline_quality <= 0.0:
            return None
        if not results:
            return None
        best_quality = max(result.quality_score.overall_score for result in results)
        return ((best_quality - baseline_quality) / baseline_quality) * 100.0


def _format_validation_errors(exc: ValidationError) -> List[str]:
    """Return human-friendly strings describing validation failures."""

    details: List[str] = []
    for error in exc.errors():
        location = " → ".join(str(segment) for segment in error.get("loc", ()))
        message = error.get("msg") or "Invalid value."
        if location:
            details.append(f"{location}: {message}")
        else:
            details.append(message)
    if not details:
        details.append(str(exc))
    return details


def _format_yaml_error(error: yaml.YAMLError) -> str:
    """Provide a concise YAML parsing error message for users."""

    problem_mark = getattr(error, "problem_mark", None)
    if problem_mark is not None:
        return (
            f"{getattr(error, 'problem', error)} (line {problem_mark.line + 1}, column {problem_mark.column + 1})"
        )
    return str(error)
