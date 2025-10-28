"""Character profile generation workflow for testing structured output formats.

Tests JSON vs. Markdown, strict vs. flexible schemas, and other structured output strategies.
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
from tesseract_flow.core.exceptions import WorkflowExecutionError
from tesseract_flow.core.strategies import GenerationStrategy, get_strategy


class CharacterProfileInput(BaseModel):
    """Input payload for character profile generation."""

    character_name: str = Field(..., min_length=1)
    character_context: Optional[str] = None
    story_genre: Optional[str] = "fantasy"
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")

    @field_validator("character_name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "Character name must be non-empty."
            raise ValueError(msg)
        return stripped


class CharacterProfileOutput(BaseModel):
    """Workflow output containing character profile."""

    profile_content: str
    evaluation_text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("profile_content")
    @classmethod
    def _normalize_content(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "Profile content must be non-empty."
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
    output_format: str
    schema_strictness: str
    nesting_depth: str
    field_descriptions: str
    validation_strategy: str
    example_provided: str
    metadata: Dict[str, Any]


class CharacterProfileWorkflow(BaseWorkflowService[CharacterProfileInput, CharacterProfileOutput]):
    """LangGraph workflow that generates structured character profiles.

    Tests different structured output strategies (JSON, Markdown, YAML) with varying
    schema strictness and validation approaches.
    """

    DEFAULT_PROMPTS: Dict[str, str] = {
        "generate_profile": (
            "Generate a character profile for: {{character_name}}\n"
            "\n"
            "{% if character_context %}Context: {{character_context}}\n{% endif %}"
            "Genre: {{story_genre}}\n"
            "\n"
            "Output Format: {{output_format}}\n"
            "Schema Strictness: {{schema_strictness}}\n"
            "Nesting: {{nesting_depth}}\n"
            "\n"
            "{% if example_provided == 'yes' %}"
            "{% if output_format == 'json' %}"
            "Example format:\n"
            "```json\n"
            "{\n"
            '  "name": "Elara Moonwhisper",\n'
            '  "age": 28,\n'
            '  "role": "Mage",\n'
            "{% if nesting_depth == 'nested' %}"
            '  "traits": {\n'
            '    "personality": ["brave", "curious"],\n'
            '    "skills": ["fire magic", "herbalism"]\n'
            '  },\n'
            '  "relationships": [\n'
            '    {"name": "Marcus", "relation": "mentor"},\n'
            '    {"name": "Lyra", "relation": "rival"}\n'
            '  ]\n'
            "{% else %}"
            '  "traits": ["brave", "curious", "analytical"],\n'
            '  "skills": ["fire magic", "herbalism", "alchemy"]\n'
            "{% endif %}"
            "}\n"
            "```\n"
            "{% else %}"
            "Example format:\n"
            "# Character Profile\n\n"
            "**Name**: Elara Moonwhisper  \n"
            "**Age**: 28  \n"
            "**Role**: Mage  \n\n"
            "## Personality\n"
            "Brave, curious, and analytical.\n\n"
            "## Skills\n"
            "- Fire magic\n"
            "- Herbalism\n"
            "- Alchemy\n"
            "{% endif %}"
            "{% endif %}\n"
            "\n"
            "{% if field_descriptions == 'present' %}"
            "Include these fields:\n"
            "- name: Character's full name\n"
            "- age: Character's age\n"
            "- role: Character's role/profession\n"
            "- traits: Personality traits and characteristics\n"
            "- skills: Abilities, powers, or expertise\n"
            "{% if nesting_depth == 'nested' %}"
            "- relationships: Array of {name, relation} objects\n"
            "{% else %}"
            "- relationships: List of key relationships\n"
            "{% endif %}"
            "{% endif %}\n"
            "\n"
            "{% if validation_strategy == 'pydantic' %}"
            "Ensure your output is strictly valid {{output_format}} that can be parsed programmatically.\n"
            "{% else %}"
            "Generate a clear, readable profile in {{output_format}} format.\n"
            "{% endif %}\n"
            "\n"
            "Generate the character profile now:\n"
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

    def prepare_input(
        self,
        test_config: TestConfiguration,
        experiment_config: ExperimentConfig | None,
    ) -> CharacterProfileInput:
        """Prepare workflow input based on test configuration."""
        values = {str(key): value for key, value in test_config.config_values.items()}
        temperature = self._coerce_float(values.get("temperature"), self._default_temperature)
        model_name = str(values.get("model", self._default_model))
        output_format = str(values.get("output_format", "json"))
        schema_strictness = str(values.get("schema_strictness", "strict"))
        nesting_depth = str(values.get("nesting_depth", "flat"))
        field_descriptions = str(values.get("field_descriptions", "present"))
        validation_strategy = str(values.get("validation_strategy", "pydantic"))
        example_provided = str(values.get("example_provided", "yes"))

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
            output_format=output_format,
            schema_strictness=schema_strictness,
            nesting_depth=nesting_depth,
            field_descriptions=field_descriptions,
            validation_strategy=validation_strategy,
            example_provided=example_provided,
            metadata=runtime_metadata,
        )

        return CharacterProfileInput(
            character_name="Kael Shadowborn",
            character_context="A mysterious rogue who haunts the shadowy underbelly of the city, working as an information broker and occasional thief.",
            story_genre="dark fantasy",
            metadata=metadata,
        )

    def _build_workflow(self) -> StateGraph:
        """Build LangGraph workflow."""
        graph = StateGraph(dict)
        graph.add_node("initialize", self._initialize_state)
        graph.add_node("generate", self._generate_profile)
        graph.add_node("finalize", self._finalize_output)

        graph.set_entry_point("initialize")
        graph.add_edge("initialize", "generate")
        graph.add_edge("generate", "finalize")
        graph.add_edge("finalize", END)

        return graph

    def _initialize_state(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        runtime = self._runtime or _RuntimeSettings(
            model=self._default_model,
            temperature=self._default_temperature,
            output_format="json",
            schema_strictness="strict",
            nesting_depth="flat",
            field_descriptions="present",
            validation_strategy="pydantic",
            example_provided="yes",
            metadata={},
        )
        input_model = CharacterProfileInput.model_validate(payload)
        return {
            "input": input_model,
            "settings": runtime,
            "profile_content": "",
            "test_config": runtime.metadata,
        }

    def _generate_profile(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate character profile in specified format."""
        runtime: _RuntimeSettings = state["settings"]
        input_model: CharacterProfileInput = state["input"]

        # Get strategy
        strategy: GenerationStrategy = get_strategy("standard")  # Always use standard for structured output

        # Build context for prompt
        context = {
            "character_name": input_model.character_name,
            "character_context": input_model.character_context or "",
            "story_genre": input_model.story_genre,
            "output_format": runtime.output_format,
            "schema_strictness": runtime.schema_strictness,
            "nesting_depth": runtime.nesting_depth,
            "field_descriptions": runtime.field_descriptions,
            "validation_strategy": runtime.validation_strategy,
            "example_provided": runtime.example_provided,
        }

        # Render prompt
        template = Template(self.DEFAULT_PROMPTS["generate_profile"])
        prompt = template.render(**context)

        # Generate
        profile_content = self._invoke_strategy(prompt, runtime)

        state.update({
            "profile_content": profile_content,
        })
        return state

    def _finalize_output(self, state: Dict[str, Any]) -> CharacterProfileOutput:
        profile_content: str = state.get("profile_content") or "No profile generated."
        input_model: CharacterProfileInput = state["input"]
        runtime: _RuntimeSettings = state["settings"]

        evaluation_text = f"Character: {input_model.character_name}\n\nFormat: {runtime.output_format}\n\nProfile:\n{profile_content}"

        return CharacterProfileOutput(
            profile_content=profile_content,
            evaluation_text=evaluation_text,
            metadata=input_model.metadata,
        )

    def _validate_output(self, result: Any) -> CharacterProfileOutput:
        return CharacterProfileOutput.model_validate(result)

    def _invoke_strategy(self, prompt: str, runtime: _RuntimeSettings) -> str:
        """Invoke generation strategy synchronously."""
        strategy = get_strategy("standard")
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
