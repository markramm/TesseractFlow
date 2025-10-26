"""Analysis utilities for interpreting experiment results."""
from __future__ import annotations

import math
from pathlib import Path
from statistics import mean
from typing import Dict, Iterable, Mapping, MutableMapping, Optional, Sequence

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from tesseract_flow.core.config import TestConfiguration, TestResult, Variable


class Effect(BaseModel):
    """Main effect metrics for a single experiment variable."""

    variable: str
    avg_level_1: float
    avg_level_2: float
    effect_size: float
    sum_of_squares: float = Field(ge=0.0)
    contribution_pct: float = Field(ge=0.0)

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def _validate_effect(self) -> "Effect":
        expected = self.avg_level_2 - self.avg_level_1
        if not math.isclose(self.effect_size, expected, rel_tol=1e-6, abs_tol=1e-9):
            msg = "effect_size must equal avg_level_2 - avg_level_1"
            raise ValueError(msg)
        return self


class MainEffects(BaseModel):
    """Collection of main effects for an experiment."""

    experiment_id: str
    effects: Dict[str, Effect]
    total_ss: float = Field(ge=0.0)

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def _validate_contributions(self) -> "MainEffects":
        if not self.effects:
            msg = "effects must contain at least one entry"
            raise ValueError(msg)

        total_pct = sum(effect.contribution_pct for effect in self.effects.values())
        if self.total_ss == 0.0:
            if total_pct != 0.0:
                msg = "Contribution percentages must be zero when total sum of squares is zero."
                raise ValueError(msg)
            return self

        if not math.isclose(total_pct, 100.0, rel_tol=1e-2, abs_tol=0.5):
            msg = "Contribution percentages must sum to approximately 100%."
            raise ValueError(msg)
        return self


class MainEffectsAnalyzer:
    """Compute Taguchi main effects from experiment results."""

    @staticmethod
    def compute(
        results: Sequence[TestResult],
        variables: Sequence[Variable],
        *,
        experiment_id: str,
    ) -> MainEffects:
        """Return main effects for ``variables`` derived from ``results``."""

        if len(results) != 8:
            msg = "Main effects analysis requires exactly 8 results for L8 array."
            raise ValueError(msg)
        if not variables:
            msg = "At least one variable is required for main effects analysis."
            raise ValueError(msg)

        effects: MutableMapping[str, Effect] = {}
        total_ss = 0.0

        for variable in variables:
            name = variable.name
            level_1, level_2 = variable.level_1, variable.level_2
            level_1_utilities = _utilities_for_level(results, name, level_1)
            level_2_utilities = _utilities_for_level(results, name, level_2)

            if not level_1_utilities or not level_2_utilities:
                msg = f"Results are missing level assignments for variable '{name}'."
                raise ValueError(msg)

            avg_1 = mean(level_1_utilities)
            avg_2 = mean(level_2_utilities)
            effect_size = avg_2 - avg_1
            sum_of_squares = (effect_size**2) * len(level_1_utilities)
            total_ss += sum_of_squares

            effects[name] = Effect(
                variable=name,
                avg_level_1=avg_1,
                avg_level_2=avg_2,
                effect_size=effect_size,
                sum_of_squares=sum_of_squares,
                contribution_pct=0.0,
            )

        if total_ss > 0.0:
            for name, effect in effects.items():
                contribution = (effect.sum_of_squares / total_ss) * 100.0
                effects[name] = effect.model_copy(update={"contribution_pct": contribution})
        else:
            # All utilities identical; contributions remain zero.
            effects = {
                name: effect.model_copy(update={"contribution_pct": 0.0})
                for name, effect in effects.items()
            }

        return MainEffects(experiment_id=experiment_id, effects=dict(effects), total_ss=total_ss)


def identify_optimal_config(main_effects: MainEffects, variables: Sequence[Variable]) -> Dict[str, object]:
    """Return the recommended configuration selecting higher-utility levels."""

    variable_lookup: Mapping[str, Variable] = {variable.name: variable for variable in variables}
    optimal: Dict[str, object] = {}
    for name, effect in main_effects.effects.items():
        variable = variable_lookup.get(name)
        if variable is None:
            msg = f"Variable '{name}' not found in experiment definition."
            raise ValueError(msg)
        if effect.avg_level_1 >= effect.avg_level_2:
            optimal[name] = variable.level_1
        else:
            optimal[name] = variable.level_2
    return optimal


def compare_configurations(
    baseline: Mapping[str, object],
    candidate: Mapping[str, object],
) -> Dict[str, Dict[str, object]]:
    """Return a comparison mapping highlighting configuration differences."""

    comparison: Dict[str, Dict[str, object]] = {}
    keys = sorted(set(baseline) | set(candidate))
    for key in keys:
        baseline_value = baseline.get(key)
        candidate_value = candidate.get(key)
        comparison[key] = {
            "baseline": baseline_value,
            "candidate": candidate_value,
            "changed": baseline_value != candidate_value,
        }
    return comparison


def calculate_quality_improvement(
    baseline_quality: Optional[float],
    optimal_quality: Optional[float],
) -> Optional[float]:
    """Compute percentage improvement from ``baseline_quality`` to ``optimal_quality``."""

    if baseline_quality is None or optimal_quality is None:
        return None
    if baseline_quality <= 0.0:
        return None
    return ((optimal_quality - baseline_quality) / baseline_quality) * 100.0


def export_optimal_config(
    optimal_values: Mapping[str, object],
    path: Path | str,
    *,
    experiment_name: str,
    workflow: str,
) -> Path:
    """Persist the recommended configuration to a YAML file."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "experiment": experiment_name,
        "workflow": workflow,
        "configuration": dict(optimal_values),
    }
    destination.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )
    return destination


def _utilities_for_level(
    results: Iterable[TestResult],
    variable_name: str,
    level_value: object,
) -> list[float]:
    utilities: list[float] = []
    for result in results:
        config: TestConfiguration = result.config
        value = config.config_values.get(variable_name)
        if value == level_value:
            utilities.append(result.utility)
    return utilities


__all__ = [
    "Effect",
    "MainEffects",
    "MainEffectsAnalyzer",
    "calculate_quality_improvement",
    "compare_configurations",
    "export_optimal_config",
    "identify_optimal_config",
]
