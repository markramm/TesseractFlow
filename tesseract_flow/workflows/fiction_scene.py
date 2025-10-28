"""Fiction scene generation workflow built on LangGraph."""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from jinja2 import Template
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, ConfigDict, Field, field_validator

from tesseract_flow.core.base_workflow import BaseWorkflowService
from tesseract_flow.core.config import ExperimentConfig, TestConfiguration, WorkflowConfig
from tesseract_flow.core.exceptions import WorkflowExecutionError


class FictionSceneInput(BaseModel):
    """Input payload for fiction scene generation."""

    scene_description: str = Field(..., min_length=1)
    characters: Optional[List[str]] = Field(default_factory=list)
    setting: Optional[str] = None
    tone: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")

    @field_validator("scene_description")
    @classmethod
    def _strip_description(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "Scene description must be a non-empty string."
            raise ValueError(msg)
        return stripped


class FictionSceneOutput(BaseModel):
    """Workflow output containing generated fiction scene."""

    scene_text: str
    evaluation_text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("scene_text")
    @classmethod
    def _normalize_scene_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "Scene text must be a non-empty string."
            raise ValueError(msg)
        return stripped

    @field_validator("evaluation_text")
    @classmethod
    def _normalize_evaluation_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "evaluation_text must be non-empty."
            raise ValueError(msg)
        return stripped

    def render_for_evaluation(self) -> str:
        """Return textual representation used for rubric evaluation."""
        return self.evaluation_text


@dataclass
class _RuntimeSettings:
    model: str
    temperature: float
    context_approach: str
    strategy_name: str
    metadata: Dict[str, Any]
    # Mixin parameters
    reasoning_enabled: bool = False
    verbalized_sampling: str = "none"
    n_samples: int = 3
    reasoning_visibility: str = "visible"
    max_reasoning_tokens: int = 1000


class FictionSceneWorkflow(BaseWorkflowService[FictionSceneInput, FictionSceneOutput]):
    """LangGraph workflow that generates fiction scenes with automatic reasoning and verbalized sampling support."""

    DEFAULT_PROMPTS: Dict[str, str] = {
        "generate": (
            "You are a skilled fiction writer. Generate a compelling scene based on the following:\n"
            "\n"
            "Scene Description: {{scene_description}}\n"
            "{% if characters %}Characters: {{characters | join(', ')}}\n{% endif %}"
            "{% if setting %}Setting: {{setting}}\n{% endif %}"
            "{% if tone %}Tone: {{tone}}\n{% endif %}"
            "{% if context %}Context: {{context}}\n{% endif %}"
            "\n"
            "Write a vivid, engaging scene that brings this description to life. Focus on:\n"
            "- Show, don't tell\n"
            "- Vivid sensory details\n"
            "- Natural character actions and reactions\n"
            "- Appropriate pacing and tension\n"
            "\n"
            "Generate the scene as plain text, no JSON or formatting."
        ),
    }

    def __init__(
        self,
        *,
        config: Optional[WorkflowConfig] = None,
        default_model: str = "openrouter/deepseek/deepseek-chat",
        default_temperature: float = 0.7,
    ) -> None:
        super().__init__(config=config)
        self._default_model = default_model
        self._default_temperature = default_temperature
        self._runtime: Optional[_RuntimeSettings] = None
        self._generated_text: Optional[str] = None
        self._generate_prompt: Optional[str] = None

    def prepare_input(
        self,
        test_config: TestConfiguration,
        experiment_config: ExperimentConfig | None,
    ) -> FictionSceneInput:
        """Prepare workflow input based on test configuration."""
        values = {str(key): value for key, value in test_config.config_values.items()}
        temperature = self._coerce_float(values.get("temperature"), self._default_temperature)
        model_name = str(values.get("model", self._default_model))
        context_approach = str(values.get("context_approach", "minimal"))
        strategy_name = str(values.get("generation_strategy", values.get("strategy", "standard")))

        # Extract mixin parameters
        reasoning_enabled = self._coerce_bool(values.get("reasoning_enabled"), False)
        verbalized_sampling = str(values.get("verbalized_sampling", "none"))
        n_samples = int(values.get("n_samples", 3))
        reasoning_visibility = str(values.get("reasoning_visibility", "visible"))

        # Determine max_reasoning_tokens based on parameter value
        max_reasoning_tokens_param = values.get("max_reasoning_tokens", "standard")
        if max_reasoning_tokens_param == "extended":
            max_reasoning_tokens = 2000
        else:  # standard
            max_reasoning_tokens = 1000

        workflow_config = experiment_config.workflow_config if experiment_config else self.config

        # Load sample scene description from config or use default
        scene_description, sample_path = self._load_sample(workflow_config)

        metadata = {
            "test_number": test_config.test_number,
            "config_values": dict(values),
        }
        runtime_metadata = {
            "test_number": test_config.test_number,
            "config": dict(values),
        }

        self._runtime = _RuntimeSettings(
            model=model_name,
            temperature=temperature,
            context_approach=context_approach,
            strategy_name=strategy_name,
            metadata=runtime_metadata,
            reasoning_enabled=reasoning_enabled,
            verbalized_sampling=verbalized_sampling,
            n_samples=n_samples,
            reasoning_visibility=reasoning_visibility,
            max_reasoning_tokens=max_reasoning_tokens,
        )
        self._generated_text = None
        self._generate_prompt = None

        return FictionSceneInput(
            scene_description=scene_description,
            characters=["Alex", "Jordan"],  # Default characters for testing
            setting="a dimly lit coffee shop",
            tone="tense but hopeful",
            metadata=metadata,
        )

    def _build_workflow(self) -> StateGraph:
        graph: StateGraph = StateGraph(dict)
        graph.add_node("initialize", self._initialize_state)
        graph.add_node("generate", self._generate_scene)
        graph.add_node("finalize", self._finalize_output)

        graph.set_entry_point("initialize")
        graph.add_edge("initialize", "generate")
        graph.add_edge("generate", "finalize")
        graph.add_edge("finalize", END)

        return graph

    def _validate_output(self, result: Any) -> FictionSceneOutput:
        return FictionSceneOutput.model_validate(result)

    def _initialize_state(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        runtime = self._runtime or _RuntimeSettings(
            model=self._default_model,
            temperature=self._default_temperature,
            context_approach="minimal",
            strategy_name="standard",
            metadata={},
        )
        input_model = FictionSceneInput.model_validate(payload)
        return {
            "input": input_model,
            "settings": runtime,
            "scene_text": "",
            "test_config": runtime.metadata,
        }

    def _generate_scene(self, state: Dict[str, Any]) -> Dict[str, Any]:
        runtime: _RuntimeSettings = state["settings"]
        input_model: FictionSceneInput = state["input"]

        # Prepare context based on context_approach
        context_text = self._prepare_context(runtime.context_approach, input_model)

        prompt = self._render_prompt(
            "generate",
            {
                "scene_description": input_model.scene_description,
                "characters": input_model.characters or [],
                "setting": input_model.setting or "",
                "tone": input_model.tone or "",
                "context": context_text,
            },
        )
        self._generate_prompt = prompt

        # Use the unified generate() method which automatically applies reasoning/sampling
        scene_text = self.generate(
            prompt=prompt,
            model=runtime.model,
            temperature=runtime.temperature,
            runtime_settings=runtime,
        )
        self._generated_text = scene_text

        state.update(
            {
                "scene_text": scene_text,
            }
        )
        return state

    def _finalize_output(self, state: Dict[str, Any]) -> FictionSceneOutput:
        scene_text: str = state.get("scene_text") or "No scene generated."
        evaluation_text = self._build_evaluation_text(scene_text)

        metadata = {
            "strategy": state["settings"].strategy_name,
            "model": state["settings"].model,
            "temperature": state["settings"].temperature,
            "context_approach": state["settings"].context_approach,
            "generation_prompt": self._generate_prompt,
            "generated_raw": self._generated_text,
            "test_config": state.get("test_config"),
        }

        clean_metadata: Dict[str, Any] = {}
        for key, value in metadata.items():
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            clean_metadata[key] = value

        return FictionSceneOutput(
            scene_text=scene_text,
            evaluation_text=evaluation_text,
            metadata=clean_metadata,
        )

    def _render_prompt(self, name: str, context: Mapping[str, Any]) -> str:
        template_source = self._prompt_templates().get(name) or self.DEFAULT_PROMPTS[name]
        template = Template(template_source)
        return template.render(**context).strip()

    def _prompt_templates(self) -> Mapping[str, str]:
        extra = getattr(self.config, "model_extra", {})
        prompts = extra.get("prompts")
        if isinstance(prompts, Mapping):
            return {str(key): str(value) for key, value in prompts.items()}
        return {}


    def _prepare_context(self, approach: str, input_model: FictionSceneInput) -> str:
        """Prepare context based on the context approach."""
        if approach == "full":
            return f"Full story context available. Characters: {', '.join(input_model.characters or [])}. Setting: {input_model.setting or 'unspecified'}."
        return "Write based on the information provided."

    def _build_evaluation_text(self, scene_text: str) -> str:
        """Build evaluation text from generated scene."""
        return f"Generated Scene:\n{scene_text}"

    def _load_sample(self, workflow_config: WorkflowConfig) -> tuple[str, Optional[str]]:
        """Load sample scene description from config."""
        sample_path = workflow_config.sample_code_path
        if not sample_path:
            # Use default test scene if no sample provided
            return "Two old friends meet after years apart, each hiding a secret.", None

        file_path = Path(sample_path)
        if not file_path.is_absolute():
            file_path = Path.cwd() / file_path
        try:
            content = file_path.read_text(encoding="utf-8")
            # Extract first line or paragraph as scene description
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            scene_desc = lines[0] if lines else "A dramatic scene unfolds."
            return scene_desc, str(file_path)
        except (FileNotFoundError, OSError):
            return "Two old friends meet after years apart, each hiding a secret.", None

    def _coerce_float(self, value: Any, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _coerce_bool(self, value: Any, default: bool) -> bool:
        """Coerce a value to boolean, handling string 'true'/'false'."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes')
        try:
            return bool(value)
        except (TypeError, ValueError):
            return default


__all__ = [
    "FictionSceneInput",
    "FictionSceneOutput",
    "FictionSceneWorkflow",
]
