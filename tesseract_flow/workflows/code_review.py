"""Code review workflow built on LangGraph."""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from jinja2 import Template
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, ConfigDict, Field, field_validator

from tesseract_flow.core.base_workflow import BaseWorkflowService
from tesseract_flow.core.config import ExperimentConfig, TestConfiguration, WorkflowConfig
from tesseract_flow.core.exceptions import WorkflowExecutionError
from tesseract_flow.core.strategies import GenerationStrategy, get_strategy


_ALLOWED_SEVERITIES = {"low", "medium", "high", "critical"}


class CodeReviewInput(BaseModel):
    """Input payload for the code review workflow."""

    code: str = Field(..., min_length=1)
    language: str = Field(default="python", min_length=1)
    context: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")

    @field_validator("code")
    @classmethod
    def _strip_code(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "Code to review must be a non-empty string."
            raise ValueError(msg)
        return stripped

    @field_validator("language")
    @classmethod
    def _normalize_language(cls, value: str) -> str:
        return value.strip()

    @field_validator("context")
    @classmethod
    def _normalize_context(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class CodeIssue(BaseModel):
    """Structured representation of an issue found during review."""

    type: str = Field(default="general", min_length=1)
    severity: str = Field(default="medium")
    description: str = Field(..., min_length=1)
    line_number: Optional[int] = Field(default=None, ge=1)
    suggestion: Optional[str] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("type")
    @classmethod
    def _normalize_type(cls, value: str) -> str:
        stripped = value.strip()
        return stripped or "general"

    @field_validator("severity")
    @classmethod
    def _validate_severity(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in _ALLOWED_SEVERITIES:
            return "medium"
        return normalized

    @field_validator("description")
    @classmethod
    def _normalize_description(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "Issue description must be a non-empty string."
            raise ValueError(msg)
        return stripped

    @field_validator("line_number", mode="before")
    @classmethod
    def _coerce_line_number(cls, value: Any) -> Optional[int]:
        if value is None:
            return None
        try:
            numeric = int(value)
        except (TypeError, ValueError):
            return None
        if numeric <= 0:
            return None
        return numeric

    @field_validator("suggestion")
    @classmethod
    def _normalize_suggestion(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class CodeReviewOutput(BaseModel):
    """Workflow output containing structured review feedback."""

    summary: str
    issues: List[CodeIssue] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    evaluation_text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("summary")
    @classmethod
    def _normalize_summary(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "Summary must be a non-empty string."
            raise ValueError(msg)
        return stripped

    @field_validator("suggestions", mode="before")
    @classmethod
    def _coerce_suggestions(cls, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, str):
            candidates = value.splitlines()
        else:
            candidates = list(value)
        normalized: List[str] = []
        for candidate in candidates:
            if not isinstance(candidate, str):
                candidate = str(candidate)
            stripped = candidate.strip()
            if stripped:
                normalized.append(stripped)
        return normalized

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
    context_size: str
    strategy_name: str
    language: str
    sample_code_path: Optional[str]
    metadata: Dict[str, Any]


class CodeReviewWorkflow(BaseWorkflowService[CodeReviewInput, CodeReviewOutput]):
    """LangGraph workflow that analyzes code and returns structured feedback."""

    DEFAULT_PROMPTS: Dict[str, str] = {
        "analyze": (
            "You are an expert reviewer of {{language}} code.\n"
            "{% if context %}Context: {{context}}\n{% endif %}"
            "Review the following snippet and identify issues.\n"
            "```{{language}}\n{{code}}\n```\n"
            "Return JSON with keys 'summary', 'issues', and 'suggestions'. Each issue should "
            "include type, severity, description, optional line_number, and suggestion."
        ),
        "suggest": (
            "Given the analysis below, enumerate actionable suggestions in JSON under "
            "the key 'suggestions'. Analysis: {{analysis}}"
        ),
    }

    def __init__(
        self,
        *,
        config: Optional[WorkflowConfig] = None,
        default_model: str = "anthropic/claude-3.5-sonnet",
        default_temperature: float = 0.3,
    ) -> None:
        super().__init__(config=config)
        self._default_model = default_model
        self._default_temperature = default_temperature
        self._runtime: Optional[_RuntimeSettings] = None
        self._analysis_text: Optional[str] = None
        self._analysis_prompt: Optional[str] = None
        self._suggest_prompt: Optional[str] = None

    def prepare_input(
        self,
        test_config: TestConfiguration,
        experiment_config: ExperimentConfig | None,
    ) -> CodeReviewInput:
        """Prepare workflow input based on test configuration."""

        values = {str(key): value for key, value in test_config.config_values.items()}
        temperature = self._coerce_float(values.get("temperature"), self._default_temperature)
        model_name = str(values.get("model", self._default_model))
        context_size = str(values.get("context_size", values.get("context", "file_only")))
        strategy_name = str(values.get("generation_strategy", values.get("strategy", "standard")))

        workflow_config = experiment_config.workflow_config if experiment_config else self.config
        language = self._resolve_language(values, workflow_config)
        code, sample_path = self._load_source(workflow_config)
        context_description = self._context_description(context_size, workflow_config)

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
            strategy_name=strategy_name,
            language=language,
            sample_code_path=sample_path,
            metadata=runtime_metadata,
        )
        self._analysis_text = None
        self._analysis_prompt = None
        self._suggest_prompt = None

        return CodeReviewInput(
            code=code,
            language=language,
            context=context_description,
            metadata=metadata,
        )

    def _build_workflow(self) -> StateGraph:
        graph: StateGraph = StateGraph(dict)
        graph.add_node("initialize", self._initialize_state)
        graph.add_node("analyze", self._analyze_code)
        graph.add_node("synthesize", self._synthesize_feedback)
        graph.add_node("finalize", self._finalize_output)

        graph.set_entry_point("initialize")
        graph.add_edge("initialize", "analyze")
        graph.add_edge("analyze", "synthesize")
        graph.add_edge("synthesize", "finalize")
        graph.add_edge("finalize", END)

        return graph

    def _validate_output(self, result: Any) -> CodeReviewOutput:
        return CodeReviewOutput.model_validate(result)

    def _initialize_state(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        runtime = self._runtime or _RuntimeSettings(
            model=self._default_model,
            temperature=self._default_temperature,
            context_size="file_only",
            strategy_name="standard",
            language="python",
            sample_code_path=None,
            metadata={},
        )
        input_model = CodeReviewInput.model_validate(payload)
        return {
            "input": input_model,
            "settings": runtime,
            "issues": [],
            "suggestions": [],
            "summary": "",
            "analysis": "",
            "analysis_structured": {},
            "test_config": runtime.metadata,
        }

    def _analyze_code(self, state: Dict[str, Any]) -> Dict[str, Any]:
        runtime: _RuntimeSettings = state["settings"]
        input_model: CodeReviewInput = state["input"]

        prompt = self._render_prompt(
            "analyze",
            {
                "code": input_model.code,
                "language": runtime.language,
                "context": input_model.context or "",
            },
        )
        self._analysis_prompt = prompt
        analysis_text = self._invoke_strategy(prompt, runtime)
        self._analysis_text = analysis_text
        structured = self._parse_analysis(analysis_text)
        issues = [self._convert_issue(item) for item in structured.get("issues", [])]
        summary = structured.get("summary") or self._summarize_issues(issues)

        state.update(
            {
                "analysis": analysis_text,
                "analysis_structured": structured,
                "issues": issues,
                "summary": summary,
            }
        )
        return state

    def _synthesize_feedback(self, state: Dict[str, Any]) -> Dict[str, Any]:
        runtime: _RuntimeSettings = state["settings"]
        structured = state.get("analysis_structured", {})
        suggestions = structured.get("suggestions")

        if suggestions is None:
            prompt = self._render_prompt(
                "suggest",
                {
                    "analysis": state.get("analysis", ""),
                    "code": state["input"].code,
                },
            )
            self._suggest_prompt = prompt
            suggestions_text = self._invoke_strategy(prompt, runtime)
            suggestions = self._parse_suggestions(suggestions_text)
        else:
            self._suggest_prompt = None

        normalized = self._normalize_suggestions(suggestions)
        state["suggestions"] = normalized
        if not state.get("summary"):
            state["summary"] = self._summarize_issues(state.get("issues", []))
        return state

    def _finalize_output(self, state: Dict[str, Any]) -> CodeReviewOutput:
        issues: List[CodeIssue] = state.get("issues", [])
        suggestions: List[str] = state.get("suggestions", [])
        summary: str = state.get("summary") or self._summarize_issues(issues)
        evaluation_text = self._build_evaluation_text(summary, issues, suggestions)

        metadata = {
            "strategy": state["settings"].strategy_name,
            "model": state["settings"].model,
            "temperature": state["settings"].temperature,
            "context_size": state["settings"].context_size,
            "language": state["settings"].language,
            "sample_code_path": state["settings"].sample_code_path,
            "analysis_prompt": self._analysis_prompt,
            "analysis_raw": self._analysis_text,
            "suggest_prompt": self._suggest_prompt,
            "test_config": state.get("test_config"),
        }

        clean_metadata: Dict[str, Any] = {}
        for key, value in metadata.items():
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            clean_metadata[key] = value
        return CodeReviewOutput(
            summary=summary,
            issues=issues,
            suggestions=suggestions,
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
            # ValueError from strategies contains detailed API error info
            raise WorkflowExecutionError(f"Generation strategy failed: {exc}") from exc
        except Exception as exc:  # pragma: no cover - defensive guard
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

    def _parse_analysis(self, response: str) -> Dict[str, Any]:
        cleaned = self._strip_code_fence(response)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            return {
                "summary": cleaned.strip() or "No significant issues identified.",
                "issues": [],
                "suggestions": [],
            }
        if not isinstance(data, Mapping):
            return {
                "summary": str(data),
                "issues": [],
                "suggestions": [],
            }
        normalized: Dict[str, Any] = {
            "summary": str(data.get("summary", "")).strip(),
        }
        raw_issues = data.get("issues") or []
        if isinstance(raw_issues, Mapping):
            raw_issues = list(raw_issues.values())
        normalized["issues"] = list(raw_issues)
        normalized["suggestions"] = data.get("suggestions")
        return normalized

    def _parse_suggestions(self, response: str) -> Iterable[str]:
        cleaned = self._strip_code_fence(response)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            return cleaned.splitlines()
        if isinstance(data, Mapping):
            candidate = data.get("suggestions")
        else:
            candidate = data
        if isinstance(candidate, Mapping):
            return candidate.values()
        if isinstance(candidate, Iterable) and not isinstance(candidate, (str, bytes)):
            return candidate
        return [str(candidate)]

    def _normalize_suggestions(self, suggestions: Any) -> List[str]:
        if suggestions is None:
            return []
        if isinstance(suggestions, Iterable) and not isinstance(suggestions, (str, bytes)):
            candidates = suggestions
        else:
            candidates = [suggestions]
        normalized: List[str] = []
        for candidate in candidates:
            if not isinstance(candidate, str):
                candidate = str(candidate)
            stripped = candidate.strip()
            if stripped:
                normalized.append(stripped)
        return normalized

    def _convert_issue(self, payload: Any) -> CodeIssue:
        if isinstance(payload, CodeIssue):
            return payload
        if not isinstance(payload, Mapping):
            return CodeIssue(description=str(payload))
        data = {
            "type": payload.get("type") or payload.get("category") or "general",
            "severity": payload.get("severity") or payload.get("level") or "medium",
            "description": payload.get("description")
            or payload.get("details")
            or payload.get("message")
            or "Issue requires attention.",
            "line_number": payload.get("line_number")
            or payload.get("line")
            or payload.get("lineNo"),
            "suggestion": payload.get("suggestion") or payload.get("fix"),
        }
        return CodeIssue(**data)

    def _summarize_issues(self, issues: Iterable[CodeIssue]) -> str:
        issue_list = list(issues)
        if not issue_list:
            return "No significant issues identified."
        severity_counts: Dict[str, int] = {}
        for issue in issue_list:
            severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1
        parts = [
            f"Identified {len(issue_list)} issue{'s' if len(issue_list) != 1 else ''}.",
            "Severity breakdown: "
            + ", ".join(f"{key}: {value}" for key, value in sorted(severity_counts.items())),
        ]
        return " ".join(parts)

    def _build_evaluation_text(
        self, summary: str, issues: Iterable[CodeIssue], suggestions: Iterable[str]
    ) -> str:
        lines = [summary]
        issues_list = list(issues)
        if issues_list:
            lines.append("Issues:")
            for issue in issues_list:
                prefix = f"- ({issue.severity}) {issue.description}"
                if issue.line_number is not None:
                    prefix += f" [line {issue.line_number}]"
                if issue.suggestion:
                    prefix += f" Suggested fix: {issue.suggestion}"
                lines.append(prefix)
        suggestions_list = list(suggestions)
        if suggestions_list:
            lines.append("Suggestions:")
            lines.extend(f"- {item}" for item in suggestions_list)
        return "\n".join(lines).strip()

    def _strip_code_fence(self, value: str) -> str:
        stripped = value.strip()
        if stripped.startswith("```") and stripped.endswith("```"):
            stripped = stripped.strip("`")
            if stripped.startswith("json"):
                stripped = stripped[4:]
        return stripped.strip()

    def _load_source(self, workflow_config: WorkflowConfig) -> tuple[str, Optional[str]]:
        sample_path = workflow_config.sample_code_path
        if not sample_path:
            msg = "Workflow configuration must define sample_code_path for code review."
            raise WorkflowExecutionError(msg)
        file_path = Path(sample_path)
        if not file_path.is_absolute():
            file_path = Path.cwd() / file_path
        try:
            content = file_path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:  # pragma: no cover - depends on env
            msg = f"Sample code file not found: {file_path}"
            raise WorkflowExecutionError(msg) from exc
        except OSError as exc:  # pragma: no cover - depends on env
            msg = f"Failed to read sample code: {file_path}"
            raise WorkflowExecutionError(msg) from exc
        return content, str(file_path)

    def _context_description(
        self, context_size: str, workflow_config: WorkflowConfig
    ) -> Optional[str]:
        context_map = {
            "file_only": "Review limited to the provided file.",
            "full_module": "Consider surrounding module context for the review.",
        }
        if context_size in context_map:
            return context_map[context_size]
        extra = getattr(workflow_config, "model_extra", {})
        descriptions = extra.get("context_descriptions")
        if isinstance(descriptions, Mapping):
            candidate = descriptions.get(context_size)
            if isinstance(candidate, str):
                return candidate.strip() or None
        return None

    def _resolve_language(
        self, values: Mapping[str, Any], workflow_config: WorkflowConfig
    ) -> str:
        if "language" in values and isinstance(values["language"], str):
            return values["language"].strip() or "python"
        extra = getattr(workflow_config, "model_extra", {})
        language = extra.get("language")
        if isinstance(language, str) and language.strip():
            return language.strip()
        return "python"

    def _coerce_float(self, value: Any, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default


__all__ = [
    "CodeIssue",
    "CodeReviewInput",
    "CodeReviewOutput",
    "CodeReviewWorkflow",
]
