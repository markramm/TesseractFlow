"""Context efficiency workflow for testing DeepSeek R1's 64K context window.

Tests how R1 handles different context sizes, content types, and retrieval strategies
to evaluate efficiency across its large context window.
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
from tesseract_flow.core.strategies import get_strategy


class ContextEfficiencyInput(BaseModel):
    """Input payload for context efficiency task."""

    context_text: str = Field(..., min_length=1)
    query: str = Field(..., min_length=1)
    context_type: str = Field(..., pattern="^(narrative|technical)$")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")

    @field_validator("context_text")
    @classmethod
    def _strip_context(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "Context text must be non-empty."
            raise ValueError(msg)
        return stripped


class ContextEfficiencyOutput(BaseModel):
    """Workflow output containing retrieved information."""

    retrieved_info: str
    answer: str
    evaluation_text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("retrieved_info")
    @classmethod
    def _normalize_retrieval(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "Retrieved info must be non-empty."
            raise ValueError(msg)
        return stripped

    def render_for_evaluation(self) -> str:
        """Return textual representation used for rubric evaluation."""
        return self.evaluation_text


@dataclass
class _RuntimeSettings:
    model: str
    temperature: float
    context_size: str
    content_type: str
    retrieval_strategy: str
    task_complexity: str
    position_bias_test: str
    compression_method: str
    metadata: Dict[str, Any]


class ContextEfficiencyWorkflow(BaseWorkflowService[ContextEfficiencyInput, ContextEfficiencyOutput]):
    """LangGraph workflow that tests R1's context window efficiency.

    Tests how DeepSeek R1 handles large context windows across different
    content types, retrieval strategies, and information positions.
    """

    # Sample contexts for testing
    NARRATIVE_CONTEXT_SMALL = """
    The detective walked into the dimly lit office. On the desk lay three clues:
    a torn photograph dated March 15th, a key marked "Storage Unit 42B", and
    a handwritten note saying "Meet me at the old lighthouse at midnight."
    """

    NARRATIVE_CONTEXT_LARGE = """
    Chapter 1: The Beginning

    Detective Sarah Chen had been investigating the Riverside case for three months.
    The evidence was scattered across multiple locations and timelines. In January,
    a witness reported seeing suspicious activity near the warehouse district.

    Chapter 2: The Middle Clues

    {}

    By February, the pattern became clearer. Multiple testimonies confirmed that
    someone was accessing Storage Unit 42B regularly. Security footage from March
    showed a person matching the suspect's description.

    Chapter 3: The Key Evidence

    On March 15th, a torn photograph was found at the crime scene. The photograph
    depicted two people standing in front of the old lighthouse - the same lighthouse
    mentioned in a handwritten note discovered later. The note read: "Meet me at
    the old lighthouse at midnight." This was the breakthrough the case needed.

    Chapter 4: Additional Context

    The investigation continued through April and May, with various leads and
    false trails. But the core evidence remained: the photograph, the key to
    Storage Unit 42B, and the note about the lighthouse meeting.
    """.format("Supporting details and witness statements filled dozens of pages. " * 50)

    TECHNICAL_CONTEXT_SMALL = """
    # API Documentation

    ## authenticate(username, password)
    Returns: auth_token (string)
    Throws: AuthError if credentials invalid

    ## get_user_data(auth_token, user_id)
    Returns: UserData object
    Requires: valid auth_token from authenticate()
    """

    TECHNICAL_CONTEXT_LARGE = """
    # Complete API Reference Documentation

    ## Overview
    This API provides comprehensive user management capabilities.
    Version: 2.1.4
    Last Updated: March 2024

    ## Authentication Endpoints

    ### authenticate(username, password)
    Primary authentication method for all API access.

    Parameters:
    - username (string): User's registered username
    - password (string): User's password (min 8 characters)

    Returns:
    - auth_token (string): JWT token valid for 24 hours

    Throws:
    - AuthError: If credentials are invalid
    - RateLimitError: If too many attempts

    Example:
    ```
    token = api.authenticate("user@example.com", "password123")
    ```

    {}

    ## User Data Endpoints

    ### get_user_data(auth_token, user_id)
    Retrieves comprehensive user information.

    Parameters:
    - auth_token (string): Valid token from authenticate()
    - user_id (integer): Target user's ID

    Returns:
    - UserData object containing:
      - user_id: integer
      - username: string
      - email: string
      - created_at: datetime
      - last_login: datetime
      - preferences: dict

    Requires:
    - Valid auth_token obtained from authenticate()
    - User must have permission to access the requested user_id

    Throws:
    - AuthError: If token is invalid or expired
    - PermissionError: If user lacks access rights
    - NotFoundError: If user_id doesn't exist

    ## Additional Documentation
    Rate limiting, error codes, and edge cases are documented in separate sections.
    """.format("Additional middleware, logging, and debugging information... " * 50)

    def __init__(
        self,
        *,
        config: Optional[WorkflowConfig] = None,
        default_model: str = "openrouter/deepseek/deepseek-r1",
        default_temperature: float = 0.2,
    ) -> None:
        super().__init__(config=config)
        self._default_model = default_model
        self._default_temperature = default_temperature
        self._runtime: Optional[_RuntimeSettings] = None

    def prepare_input(
        self,
        test_config: TestConfiguration,
        experiment_config: ExperimentConfig | None,
    ) -> ContextEfficiencyInput:
        """Prepare workflow input based on test configuration."""
        values = {str(key): value for key, value in test_config.config_values.items()}
        temperature = self._coerce_float(values.get("temperature"), self._default_temperature)
        model_name = str(values.get("model", self._default_model))
        context_size = str(values.get("context_size", "small"))
        content_type = str(values.get("content_type", "narrative"))
        retrieval_strategy = str(values.get("retrieval_strategy", "full_context"))
        task_complexity = str(values.get("task_complexity", "simple"))
        position_bias_test = str(values.get("position_bias_test", "beginning"))
        compression_method = str(values.get("compression_method", "none"))

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
            context_size=context_size,
            content_type=content_type,
            retrieval_strategy=retrieval_strategy,
            task_complexity=task_complexity,
            position_bias_test=position_bias_test,
            compression_method=compression_method,
            metadata=runtime_metadata,
        )

        # Select context based on size and content type
        if content_type == "narrative":
            if context_size == "small":
                context_text = self.NARRATIVE_CONTEXT_SMALL
                query = "What three clues did the detective find?"
            else:
                context_text = self.NARRATIVE_CONTEXT_LARGE
                query = "What was the key evidence found on March 15th and what did the note say?"
        else:  # technical
            if context_size == "small":
                context_text = self.TECHNICAL_CONTEXT_SMALL
                query = "What does the authenticate function return and what error does it throw?"
            else:
                context_text = self.TECHNICAL_CONTEXT_LARGE
                query = "What does get_user_data require and what errors can it throw?"

        return ContextEfficiencyInput(
            context_text=context_text,
            query=query,
            context_type=content_type,
            metadata=metadata,
        )

    def _build_workflow(self) -> StateGraph:
        """Build LangGraph workflow."""
        graph = StateGraph(dict)
        graph.add_node("initialize", self._initialize_state)
        graph.add_node("retrieve", self._retrieve_information)
        graph.add_node("answer", self._generate_answer)
        graph.add_node("finalize", self._finalize_output)

        graph.set_entry_point("initialize")
        graph.add_edge("initialize", "retrieve")
        graph.add_edge("retrieve", "answer")
        graph.add_edge("answer", "finalize")
        graph.add_edge("finalize", END)

        return graph

    def _initialize_state(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        runtime = self._runtime or _RuntimeSettings(
            model=self._default_model,
            temperature=self._default_temperature,
            context_size="small",
            content_type="narrative",
            retrieval_strategy="full_context",
            task_complexity="simple",
            position_bias_test="beginning",
            compression_method="none",
            metadata={},
        )
        input_model = ContextEfficiencyInput.model_validate(payload)
        return {
            "input": input_model,
            "settings": runtime,
            "retrieved_info": "",
            "answer": "",
            "test_config": runtime.metadata,
        }

    def _retrieve_information(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve information from context."""
        runtime: _RuntimeSettings = state["settings"]
        input_model: ContextEfficiencyInput = state["input"]

        retrieval_prompt = f"""Given the following context, identify the key information needed to answer the query.

Context:
{input_model.context_text}

Query: {input_model.query}

Extract the relevant information from the context that directly answers this query."""

        retrieved = self._invoke_strategy(retrieval_prompt, runtime, max_tokens=500)
        state["retrieved_info"] = retrieved
        return state

    def _generate_answer(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate final answer using retrieved information."""
        runtime: _RuntimeSettings = state["settings"]
        input_model: ContextEfficiencyInput = state["input"]
        retrieved_info: str = state["retrieved_info"]

        answer_prompt = f"""Based on the retrieved information, provide a complete answer to the query.

Retrieved Information:
{retrieved_info}

Query: {input_model.query}

Provide a clear, complete answer."""

        answer = self._invoke_strategy(answer_prompt, runtime, max_tokens=300)
        state["answer"] = answer
        return state

    def _finalize_output(self, state: Dict[str, Any]) -> ContextEfficiencyOutput:
        retrieved_info: str = state.get("retrieved_info") or "(no info retrieved)"
        answer: str = state.get("answer") or "No answer generated."
        input_model: ContextEfficiencyInput = state["input"]
        runtime: _RuntimeSettings = state["settings"]

        evaluation_text = (
            f"Context Size: {runtime.context_size}\n"
            f"Content Type: {runtime.content_type}\n"
            f"Retrieval Strategy: {runtime.retrieval_strategy}\n"
            f"Task Complexity: {runtime.task_complexity}\n\n"
            f"Query: {input_model.query}\n\n"
            f"Retrieved Information:\n{retrieved_info}\n\n"
            f"Final Answer:\n{answer}"
        )

        return ContextEfficiencyOutput(
            retrieved_info=retrieved_info,
            answer=answer,
            evaluation_text=evaluation_text,
            metadata=input_model.metadata,
        )

    def _validate_output(self, result: Any) -> ContextEfficiencyOutput:
        return ContextEfficiencyOutput.model_validate(result)

    def _invoke_strategy(self, prompt: str, runtime: _RuntimeSettings, max_tokens: int = 500) -> str:
        """Invoke generation strategy synchronously."""
        strategy = get_strategy("standard")
        parameters = {
            "temperature": runtime.temperature,
            "max_tokens": max_tokens,
        }
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
