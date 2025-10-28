"""Dialogue enhancement workflow built on LangGraph."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from jinja2 import Template
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, ConfigDict, Field, field_validator

from tesseract_flow.core.base_workflow import BaseWorkflowService
from tesseract_flow.core.config import ExperimentConfig, TestConfiguration, WorkflowConfig
from tesseract_flow.core.exceptions import WorkflowExecutionError
from tesseract_flow.core.strategies import GenerationStrategy, get_strategy


class DialogueEnhancementInput(BaseModel):
    """Input payload for dialogue enhancement."""

    original_dialogue: str = Field(..., min_length=1)
    characters: Optional[List[str]] = Field(default_factory=list)
    scene_context: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")

    @field_validator("original_dialogue")
    @classmethod
    def _strip_dialogue(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "Dialogue must be a non-empty string."
            raise ValueError(msg)
        return stripped


class DialogueEnhancementOutput(BaseModel):
    """Workflow output containing enhanced dialogue."""

    enhanced_dialogue: str
    evaluation_text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("enhanced_dialogue")
    @classmethod
    def _normalize_dialogue(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "Enhanced dialogue must be a non-empty string."
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
    voice_emphasis: str
    examples_count: str
    strategy_name: str
    metadata: Dict[str, Any]


class DialogueEnhancementWorkflow(BaseWorkflowService[DialogueEnhancementInput, DialogueEnhancementOutput]):
    """LangGraph workflow that enhances dialogue for voice distinctiveness and natural flow."""

    DEFAULT_PROMPTS: Dict[str, str] = {
        "enhance": (
            "You are a dialogue specialist. Enhance the following dialogue to make it more natural, "
            "distinctive, and emotionally authentic.\n"
            "\n"
            "Original Dialogue:\n{{original_dialogue}}\n"
            "\n"
            "{% if characters %}Characters: {{characters | join(', ')}}\n{% endif %}"
            "{% if scene_context %}Scene Context: {{scene_context}}\n{% endif %}"
            "{% if voice_emphasis == 'explicit' %}"
            "Focus heavily on making each character's voice unique and identifiable without attribution. "
            "Give each character distinct speech patterns, vocabulary, and rhythm.\n"
            "{% else %}"
            "Maintain natural dialogue flow with subtle character voice differences.\n"
            "{% endif %}"
            "{% if examples_count != '0' %}"
            "\nExamples of strong dialogue:\n"
            "1. 'You think I don't know?' vs 'You believe I am unaware?'\n"
            "2. 'Yeah, sure.' vs 'I suppose that's acceptable.'\n"
            "3. 'Get out.' vs 'I must insist you leave immediately.'\n"
            "{% endif %}"
            "\n"
            "Enhance the dialogue focusing on:\n"
            "- Voice distinctiveness (can you identify each speaker?)\n"
            "- Natural flow (realistic pacing, organic topic shifts)\n"
            "- Emotional authenticity (subtext, genuine emotions)\n"
            "\n"
            "Return only the enhanced dialogue, no additional commentary."
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
        self._enhanced_text: Optional[str] = None
        self._enhance_prompt: Optional[str] = None

    def prepare_input(
        self,
        test_config: TestConfiguration,
        experiment_config: ExperimentConfig | None,
    ) -> DialogueEnhancementInput:
        """Prepare workflow input based on test configuration."""
        values = {str(key): value for key, value in test_config.config_values.items()}
        temperature = self._coerce_float(values.get("temperature"), self._default_temperature)
        model_name = str(values.get("model", self._default_model))
        voice_emphasis = str(values.get("voice_emphasis", "subtle"))
        examples_count = str(values.get("examples_count", "0"))
        strategy_name = str(values.get("generation_strategy", values.get("strategy", "standard")))

        workflow_config = experiment_config.workflow_config if experiment_config else self.config

        # Load sample dialogue from config or use default
        original_dialogue, sample_path = self._load_sample(workflow_config)

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
            voice_emphasis=voice_emphasis,
            examples_count=examples_count,
            strategy_name=strategy_name,
            metadata=runtime_metadata,
        )
        self._enhanced_text = None
        self._enhance_prompt = None

        return DialogueEnhancementInput(
            original_dialogue=original_dialogue,
            characters=["Sarah", "Marcus"],  # Default characters for testing
            scene_context="tense negotiation in a downtown office",
            metadata=metadata,
        )

    def _build_workflow(self) -> StateGraph:
        graph: StateGraph = StateGraph(dict)
        graph.add_node("initialize", self._initialize_state)
        graph.add_node("enhance", self._enhance_dialogue)
        graph.add_node("finalize", self._finalize_output)

        graph.set_entry_point("initialize")
        graph.add_edge("initialize", "enhance")
        graph.add_edge("enhance", "finalize")
        graph.add_edge("finalize", END)

        return graph

    def _validate_output(self, result: Any) -> DialogueEnhancementOutput:
        return DialogueEnhancementOutput.model_validate(result)

    def _initialize_state(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        runtime = self._runtime or _RuntimeSettings(
            model=self._default_model,
            temperature=self._default_temperature,
            voice_emphasis="subtle",
            examples_count="0",
            strategy_name="standard",
            metadata={},
        )
        input_model = DialogueEnhancementInput.model_validate(payload)
        return {
            "input": input_model,
            "settings": runtime,
            "enhanced_dialogue": "",
            "test_config": runtime.metadata,
        }

    def _enhance_dialogue(self, state: Dict[str, Any]) -> Dict[str, Any]:
        runtime: _RuntimeSettings = state["settings"]
        input_model: DialogueEnhancementInput = state["input"]

        prompt = self._render_prompt(
            "enhance",
            {
                "original_dialogue": input_model.original_dialogue,
                "characters": input_model.characters or [],
                "scene_context": input_model.scene_context or "",
                "voice_emphasis": runtime.voice_emphasis,
                "examples_count": runtime.examples_count,
            },
        )
        self._enhance_prompt = prompt
        enhanced_text = self._invoke_strategy(prompt, runtime)
        self._enhanced_text = enhanced_text

        state.update(
            {
                "enhanced_dialogue": enhanced_text,
            }
        )
        return state

    def _finalize_output(self, state: Dict[str, Any]) -> DialogueEnhancementOutput:
        enhanced_dialogue: str = state.get("enhanced_dialogue") or "No dialogue generated."
        evaluation_text = self._build_evaluation_text(enhanced_dialogue)

        metadata = {
            "strategy": state["settings"].strategy_name,
            "model": state["settings"].model,
            "temperature": state["settings"].temperature,
            "voice_emphasis": state["settings"].voice_emphasis,
            "examples_count": state["settings"].examples_count,
            "enhance_prompt": self._enhance_prompt,
            "enhanced_raw": self._enhanced_text,
            "test_config": state.get("test_config"),
        }

        clean_metadata: Dict[str, Any] = {}
        for key, value in metadata.items():
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            clean_metadata[key] = value

        return DialogueEnhancementOutput(
            enhanced_dialogue=enhanced_dialogue,
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

    def _invoke_strategy(self, prompt: str, runtime: _RuntimeSettings) -> str:
        strategy = self._resolve_strategy(runtime.strategy_name)
        parameters = {"temperature": runtime.temperature}
        try:
            return self._await_coroutine(
                strategy.generate(
                    prompt,
                    model=runtime.model,
                    config=parameters,
                )
            )
        except ValueError as exc:
            raise WorkflowExecutionError(f"Generation strategy failed: {exc}") from exc
        except Exception as exc:
            raise WorkflowExecutionError(
                f"Generation strategy failed: {type(exc).__name__}: {exc}"
            ) from exc

    def _resolve_strategy(self, name: str) -> GenerationStrategy:
        try:
            return get_strategy(name)
        except ValueError as exc:
            raise WorkflowExecutionError(f"Unknown generation strategy: {name}") from exc

    def _await_coroutine(self, coroutine: Any) -> str:
        try:
            return asyncio.run(coroutine)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(coroutine)
            finally:
                loop.close()

    def _build_evaluation_text(self, dialogue: str) -> str:
        """Build evaluation text from enhanced dialogue."""
        return f"Enhanced Dialogue:\n{dialogue}"

    def _load_sample(self, workflow_config: WorkflowConfig) -> tuple[str, Optional[str]]:
        """Load sample dialogue from config."""
        sample_path = workflow_config.sample_code_path
        if not sample_path:
            # Use default test dialogue if no sample provided
            default_dialogue = """
"We need to talk."
"About what?"
"You know what."
"I really don't."
"""
            return default_dialogue.strip(), None

        file_path = Path(sample_path)
        if not file_path.is_absolute():
            file_path = Path.cwd() / file_path
        try:
            content = file_path.read_text(encoding="utf-8")
            return content[:500], str(file_path)  # Use first 500 chars as sample
        except (FileNotFoundError, OSError):
            default_dialogue = """
"We need to talk."
"About what?"
"You know what."
"I really don't."
"""
            return default_dialogue.strip(), None

    def _coerce_float(self, value: Any, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default


__all__ = [
    "DialogueEnhancementInput",
    "DialogueEnhancementOutput",
    "DialogueEnhancementWorkflow",
]
