"""Lore expansion workflow for extracting characters, locations, and worldbuilding from fiction.

This workflow is inspired by storypunk-app's lorebook system, which extracts structured
entities from story text to build a knowledge base for AI-assisted writing.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, Optional

from jinja2 import Template
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, ConfigDict, Field, field_validator

from tesseract_flow.core.base_workflow import BaseWorkflowService
from tesseract_flow.core.config import ExperimentConfig, TestConfiguration, WorkflowConfig
from tesseract_flow.core.strategies import GenerationStrategy, get_strategy


class LoreExpansionInput(BaseModel):
    """Input payload for lore expansion."""

    source_text: str = Field(..., min_length=1)
    story_context: Optional[str] = None
    expansion_focus: Optional[str] = "comprehensive"  # comprehensive or targeted
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")

    @field_validator("source_text")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "Source text must be a non-empty string."
            raise ValueError(msg)
        return stripped


class LoreExpansionOutput(BaseModel):
    """Workflow output containing extracted lorebook entities."""

    extracted_content: str
    evaluation_text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("extracted_content")
    @classmethod
    def _normalize_content(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "Extracted content must be non-empty."
            raise ValueError(msg)
        return stripped

    @field_validator("evaluation_text")
    @classmethod
    def _normalize_evaluation(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "Evaluation text must be non-empty."
            raise ValueError(msg)
        return stripped

    def render_for_evaluation(self) -> str:
        """Return textual representation used for rubric evaluation."""
        return self.evaluation_text


@dataclass
class _RuntimeSettings:
    model: str
    temperature: float
    generation_strategy: str
    expansion_type: str
    context_inclusion: str
    output_structure: str
    entity_detection: str
    relationship_depth: str
    metadata: Dict[str, Any]


class LoreExpansionWorkflow(BaseWorkflowService[LoreExpansionInput, LoreExpansionOutput]):
    """LangGraph workflow that extracts lorebook entities from fiction text.

    This workflow identifies characters, locations, relationships, and worldbuilding
    elements from story text, similar to storypunk-app's lore expansion system.
    """

    DEFAULT_PROMPTS: Dict[str, str] = {
        "extract": (
            "You are an expert at analyzing fiction and extracting structured worldbuilding information.\n"
            "\n"
            "Analyze the following story text and extract lorebook entities:\n"
            "\n"
            "{{source_text}}\n"
            "\n"
            "{% if story_context %}Story Context: {{story_context}}\n{% endif %}"
            "\n"
            "Extract the following types of entities:\n"
            "- **Characters**: Names, roles, key traits, relationships\n"
            "- **Locations**: Places, settings, atmosphere, significance\n"
            "- **Worldbuilding**: Rules, magic systems, technology, culture\n"
            "- **Themes**: Central ideas, motifs, symbols\n"
            "\n"
            "Focus on: {{expansion_focus}} expansion\n"
            "Output format: {{output_structure}}\n"
            "Entity detection approach: {{entity_detection}}\n"
            "Relationship detail level: {{relationship_depth}}\n"
            "\n"
            "Provide complete, accurate, and consistent information extracted directly from the text.\n"
            "Do not hallucinate details not present in the source material.\n"
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
        self._extracted_content: Optional[str] = None
        self._extract_prompt: Optional[str] = None

    def prepare_input(
        self,
        test_config: TestConfiguration,
        experiment_config: ExperimentConfig | None,
    ) -> LoreExpansionInput:
        """Prepare workflow input based on test configuration."""
        values = {str(key): value for key, value in test_config.config_values.items()}
        temperature = self._coerce_float(values.get("temperature"), self._default_temperature)
        model_name = str(values.get("model", self._default_model))
        generation_strategy = str(values.get("generation_strategy", "standard"))
        expansion_type = str(values.get("expansion_type", "comprehensive"))
        context_inclusion = str(values.get("context_inclusion", "scene_only"))
        output_structure = str(values.get("output_structure", "json"))
        entity_detection = str(values.get("entity_detection", "explicit_prompt"))
        relationship_depth = str(values.get("relationship_depth", "basic"))

        workflow_config = experiment_config.workflow_config if experiment_config else self.config

        # Load sample text from config or use default
        sample_text = self._load_sample_text(workflow_config)

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
            generation_strategy=generation_strategy,
            expansion_type=expansion_type,
            context_inclusion=context_inclusion,
            output_structure=output_structure,
            entity_detection=entity_detection,
            relationship_depth=relationship_depth,
            metadata=runtime_metadata,
        )
        self._extracted_content = None
        self._extract_prompt = None

        return LoreExpansionInput(
            source_text=sample_text,
            story_context="Fantasy fiction with magic and political intrigue",
            expansion_focus=expansion_type,
            metadata=metadata,
        )

    def _build_workflow(self) -> StateGraph:
        """Build LangGraph workflow."""
        graph: StateGraph = StateGraph(dict)
        graph.add_node("initialize", self._initialize_state)
        graph.add_node("extract", self._extract_entities)
        graph.add_node("finalize", self._finalize_output)

        graph.set_entry_point("initialize")
        graph.add_edge("initialize", "extract")
        graph.add_edge("extract", "finalize")
        graph.add_edge("finalize", END)

        return graph

    def _validate_output(self, result: Any) -> LoreExpansionOutput:
        return LoreExpansionOutput.model_validate(result)

    def _initialize_state(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        runtime = self._runtime or _RuntimeSettings(
            model=self._default_model,
            temperature=self._default_temperature,
            generation_strategy="standard",
            expansion_type="comprehensive",
            context_inclusion="scene_only",
            output_structure="json",
            entity_detection="explicit_prompt",
            relationship_depth="basic",
            metadata={},
        )
        input_model = LoreExpansionInput.model_validate(payload)
        return {
            "input": input_model,
            "settings": runtime,
            "extracted_content": "",
            "test_config": runtime.metadata,
        }

    def _extract_entities(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Extract lorebook entities from source text."""
        runtime: _RuntimeSettings = state["settings"]
        input_model: LoreExpansionInput = state["input"]

        # Get strategy
        strategy: GenerationStrategy = get_strategy(runtime.generation_strategy)

        # Build context for prompt
        context = {
            "source_text": input_model.source_text,
            "story_context": input_model.story_context or "",
            "expansion_focus": runtime.expansion_type,
            "output_structure": runtime.output_structure,
            "entity_detection": runtime.entity_detection,
            "relationship_depth": runtime.relationship_depth,
        }

        # Render prompt - always use DEFAULT_PROMPTS for now
        # In the future, could add support for custom prompts via config
        template = Template(self.DEFAULT_PROMPTS["extract"])
        prompt = template.render(**context)
        self._extract_prompt = prompt

        # Generate
        extracted_content = self._invoke_strategy(prompt, runtime)
        self._extracted_content = extracted_content

        state.update({
            "extracted_content": extracted_content,
        })
        return state

    def _finalize_output(self, state: Dict[str, Any]) -> LoreExpansionOutput:
        extracted_content: str = state.get("extracted_content") or "No content extracted."
        input_model: LoreExpansionInput = state["input"]

        evaluation_text = f"Source Text:\n{input_model.source_text}\n\nExtracted Lorebook:\n{extracted_content}"

        return LoreExpansionOutput(
            extracted_content=extracted_content,
            evaluation_text=evaluation_text,
            metadata=input_model.metadata,
        )

    def _invoke_strategy(self, prompt: str, runtime: _RuntimeSettings) -> str:
        """Invoke generation strategy synchronously."""
        strategy = get_strategy(runtime.generation_strategy)
        parameters = {"temperature": runtime.temperature}
        return self._await_coroutine(
            strategy.generate(
                prompt,
                model=runtime.model,
                config=parameters,
            )
        )

    @staticmethod
    def _await_coroutine(coroutine: Any) -> str:
        """Execute async coroutine synchronously."""
        try:
            return asyncio.run(coroutine)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(coroutine)
            finally:
                loop.close()

    @staticmethod
    def _coerce_float(value: Any, default: float) -> float:
        """Coerce value to float with fallback."""
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _load_sample_text(self, workflow_config: Optional[WorkflowConfig]) -> str:
        """Load sample text from config or use default."""
        # For now, always use default sample text
        # In the future, we could load from workflow_config.sample_code_path if needed
        return _get_default_sample_text()


def _get_default_sample_text() -> str:
    """Return default sample fiction text for testing."""
    return """The tavern fell silent as the cloaked figure entered. Elara recognized the silver clasp immediately—the mark of the Shadow Council. She gripped her dagger beneath the table, mind racing. If they'd found her here in Ravenport, her cover was blown.

The stranger's eyes swept the room, lingering on each patron before settling on the innkeeper. "I seek passage to the Shattered Isles," they said, voice low and urgent. "The old routes through Darkwater Marsh are no longer safe."

Innkeeper Greaves wiped his hands nervously. "The marsh has been cursed since the war, stranger. None who enter return unchanged." He glanced toward Elara's corner, a warning in his eyes.

Elara's fingers tightened on her blade. The Shattered Isles. That's where the prophecy said the ancient artifact lay hidden—the Soulstone that could either save or doom their world. And now the Shadow Council was hunting for it too."""
