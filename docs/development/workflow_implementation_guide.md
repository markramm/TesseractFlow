# TesseractFlow Workflow Implementation Guide

**Last Updated:** 2025-10-28
**Status:** Canonical Reference
**Applies To:** v0.1+

This guide documents the correct pattern for implementing TesseractFlow workflows based on the canonical `fiction_scene.py` implementation and validated through Wave 2 workflows (lore_expansion, multi_task_benchmark, character_profile, multi_domain).

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Core Pattern](#core-pattern)
3. [Step-by-Step Implementation](#step-by-step-implementation)
4. [Common Mistakes](#common-mistakes)
5. [Reference Examples](#reference-examples)
6. [Testing Checklist](#testing-checklist)

---

## Architecture Overview

### Key Components

```
BaseWorkflowService[TInput, TOutput]  ← Generic abstract base class
    ↓
YourWorkflow(BaseWorkflowService[YourInput, YourOutput])
    ├── prepare_input()      → Creates TInput from TestConfiguration
    ├── _build_workflow()    → Returns LangGraph StateGraph
    ├── _validate_output()   → Validates TOutput from workflow result
    └── _runtime             → Instance variable holding runtime settings
```

### State Flow

```
TestConfiguration (experiment YAML)
    ↓
prepare_input(test_config) → Creates TInput + stores _RuntimeSettings
    ↓
LangGraph.invoke(TInput.dict())
    ↓
StateGraph nodes (synchronous `def` functions):
    1. _initialize_state    → Validates input, loads _runtime
    2. _execute_task       → Calls generation strategy
    3. _finalize_output    → Returns TOutput
    ↓
_validate_output(result) → Returns TOutput
```

---

## Core Pattern

### 1. Input/Output Models (Pydantic)

```python
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Dict, Any, Optional

class YourWorkflowInput(BaseModel):
    """Input payload for your workflow."""

    task_description: str = Field(..., min_length=1)
    context: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")

    @field_validator("task_description")
    @classmethod
    def _strip_description(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Task description must be non-empty.")
        return stripped


class YourWorkflowOutput(BaseModel):
    """Workflow output containing result."""

    result: str
    evaluation_text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("result")
    @classmethod
    def _normalize_result(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Result must be non-empty.")
        return stripped

    @field_validator("evaluation_text")
    @classmethod
    def _normalize_evaluation(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Evaluation text must be non-empty.")
        return stripped

    def render_for_evaluation(self) -> str:
        """Return textual representation for rubric evaluation."""
        return self.evaluation_text
```

**Key Points:**
- `extra="allow"` on Input models (allows experiment framework to inject metadata)
- `validate_assignment=True` on Output models (validates on modification)
- All string fields must strip whitespace and validate non-empty
- Output must implement `render_for_evaluation()` method

---

### 2. Runtime Settings Dataclass

```python
from dataclasses import dataclass

@dataclass
class _RuntimeSettings:
    """Private runtime settings extracted from test configuration."""
    model: str
    temperature: float
    generation_strategy: str
    # ... other experiment variables
    metadata: Dict[str, Any]
```

**Key Points:**
- Use `@dataclass` (simpler than Pydantic for internal state)
- Prefix with `_` to indicate private/internal use
- Store ALL experiment variables here
- Include metadata dict for test tracking

---

### 3. Workflow Class Structure

```python
from tesseract_flow.core.base_workflow import BaseWorkflowService
from tesseract_flow.core.config import ExperimentConfig, TestConfiguration, WorkflowConfig
from tesseract_flow.core.strategies import GenerationStrategy, get_strategy
from langgraph.graph import END, StateGraph
import asyncio
from typing import Any, Dict, Optional

class YourWorkflow(BaseWorkflowService[YourWorkflowInput, YourWorkflowOutput]):
    """LangGraph workflow that does something interesting.

    Tests how variable_X and variable_Y affect quality in task_domain.
    """

    DEFAULT_PROMPTS: Dict[str, str] = {
        "task_prompt": (
            "You are an AI assistant.\\n"
            "\\n"
            "Task: {{task_description}}\\n"
            "{% if context %}Context: {{context}}\\n{% endif %}"
            "\\n"
            "Complete the task now:\\n"
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
    ) -> YourWorkflowInput:
        """Prepare workflow input based on test configuration."""
        # Extract config values
        values = {str(key): value for key, value in test_config.config_values.items()}

        # Coerce types with defaults
        temperature = self._coerce_float(values.get("temperature"), self._default_temperature)
        model_name = str(values.get("model", self._default_model))
        generation_strategy = str(values.get("generation_strategy", "standard"))

        # Build metadata for tracking
        metadata = {
            "test_number": test_config.test_number,
            "config_values": dict(values),
        }
        runtime_metadata = {
            "test_number": test_config.test_number,
            "config": dict(values),
        }

        # CRITICAL: Store runtime settings in instance variable
        self._runtime = _RuntimeSettings(
            model=model_name,
            temperature=temperature,
            generation_strategy=generation_strategy,
            metadata=runtime_metadata,
        )

        # Return Input model
        return YourWorkflowInput(
            task_description="Your task here",
            context="Optional context",
            metadata=metadata,
        )

    def _build_workflow(self) -> StateGraph:
        """Build LangGraph workflow."""
        graph = StateGraph(dict)
        graph.add_node("initialize", self._initialize_state)
        graph.add_node("execute", self._execute_task)
        graph.add_node("finalize", self._finalize_output)

        graph.set_entry_point("initialize")
        graph.add_edge("initialize", "execute")
        graph.add_edge("execute", "finalize")
        graph.add_edge("finalize", END)

        return graph

    def _initialize_state(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize workflow state from input payload."""
        # Load runtime or use defaults
        runtime = self._runtime or _RuntimeSettings(
            model=self._default_model,
            temperature=self._default_temperature,
            generation_strategy="standard",
            metadata={},
        )

        # Validate input
        input_model = YourWorkflowInput.model_validate(payload)

        # Return state dict
        return {
            "input": input_model,
            "settings": runtime,
            "result": "",
            "test_config": runtime.metadata,
        }

    def _execute_task(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute task using configured generation strategy."""
        runtime: _RuntimeSettings = state["settings"]
        input_model: YourWorkflowInput = state["input"]

        # Get generation strategy
        strategy: GenerationStrategy = get_strategy(runtime.generation_strategy)

        # Build prompt context
        from jinja2 import Template
        template = Template(self.DEFAULT_PROMPTS["task_prompt"])
        prompt = template.render(
            task_description=input_model.task_description,
            context=input_model.context or "",
        )

        # Generate (synchronously invoke async strategy)
        result = self._invoke_strategy(prompt, runtime)

        # Update state
        state.update({"result": result})
        return state

    def _finalize_output(self, state: Dict[str, Any]) -> YourWorkflowOutput:
        """Finalize workflow output."""
        result: str = state.get("result") or "No result generated."
        input_model: YourWorkflowInput = state["input"]
        runtime: _RuntimeSettings = state["settings"]

        evaluation_text = f"Task: {input_model.task_description}\\n\\nResult:\\n{result}"

        return YourWorkflowOutput(
            result=result,
            evaluation_text=evaluation_text,
            metadata=input_model.metadata,
        )

    def _validate_output(self, result: Any) -> YourWorkflowOutput:
        """Validate workflow output."""
        return YourWorkflowOutput.model_validate(result)

    def _invoke_strategy(self, prompt: str, runtime: _RuntimeSettings) -> str:
        """Invoke generation strategy synchronously."""
        strategy = get_strategy(runtime.generation_strategy)

        # CRITICAL: Pass temperature via config dict, NOT as direct parameter
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
            # Handle case where event loop already running
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
```

---

## Step-by-Step Implementation

### Step 1: Define Input/Output Models

Create Pydantic models with:
- Field validators for all string fields (strip + non-empty check)
- `extra="allow"` on Input
- `validate_assignment=True` on Output
- `render_for_evaluation()` method on Output

### Step 2: Create Runtime Settings Dataclass

```python
@dataclass
class _RuntimeSettings:
    model: str
    temperature: float
    # ... all experiment variables
    metadata: Dict[str, Any]
```

### Step 3: Implement `__init__()`

```python
def __init__(self, *, config: Optional[WorkflowConfig] = None, default_model: str = "...", default_temperature: float = 0.7):
    super().__init__(config=config)
    self._default_model = default_model
    self._default_temperature = default_temperature
    self._runtime: Optional[_RuntimeSettings] = None
```

### Step 4: Implement `prepare_input()`

```python
def prepare_input(self, test_config: TestConfiguration, experiment_config: ExperimentConfig | None) -> YourInput:
    # 1. Extract config values
    values = {str(key): value for key, value in test_config.config_values.items()}

    # 2. Coerce types with defaults
    temperature = self._coerce_float(values.get("temperature"), self._default_temperature)

    # 3. Build metadata
    metadata = {"test_number": test_config.test_number, "config_values": dict(values)}

    # 4. STORE runtime settings
    self._runtime = _RuntimeSettings(...)

    # 5. Return Input model
    return YourInput(...)
```

### Step 5: Build LangGraph Workflow

```python
def _build_workflow(self) -> StateGraph:
    graph = StateGraph(dict)
    graph.add_node("initialize", self._initialize_state)
    graph.add_node("execute", self._execute_task)
    graph.add_node("finalize", self._finalize_output)

    graph.set_entry_point("initialize")
    graph.add_edge("initialize", "execute")
    graph.add_edge("execute", "finalize")
    graph.add_edge("finalize", END)

    return graph
```

### Step 6: Implement LangGraph Nodes

**All nodes must be synchronous `def` functions (not `async def`)**

```python
def _initialize_state(self, payload: Dict[str, Any]) -> Dict[str, Any]:
    runtime = self._runtime or _RuntimeSettings(...)  # Fallback to defaults
    input_model = YourInput.model_validate(payload)
    return {
        "input": input_model,
        "settings": runtime,
        "result": "",
        "test_config": runtime.metadata,
    }

def _execute_task(self, state: Dict[str, Any]) -> Dict[str, Any]:
    runtime: _RuntimeSettings = state["settings"]
    input_model: YourInput = state["input"]

    # Render prompt with Jinja2
    from jinja2 import Template
    template = Template(self.DEFAULT_PROMPTS["..."])
    prompt = template.render(...)

    # Generate
    result = self._invoke_strategy(prompt, runtime)

    state.update({"result": result})
    return state

def _finalize_output(self, state: Dict[str, Any]) -> YourOutput:
    result = state.get("result") or "No result generated."
    # ... build evaluation_text
    return YourOutput(...)
```

### Step 7: Implement Helper Methods

```python
def _validate_output(self, result: Any) -> YourOutput:
    return YourOutput.model_validate(result)

def _invoke_strategy(self, prompt: str, runtime: _RuntimeSettings) -> str:
    strategy = get_strategy(runtime.generation_strategy)
    parameters = {"temperature": runtime.temperature}  # PASS AS CONFIG DICT
    return self._await_coroutine(
        strategy.generate(prompt, model=runtime.model, config=parameters)
    )

@staticmethod
def _await_coroutine(coroutine: Any) -> str:
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
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
```

### Step 8: Register Workflow

In `tesseract_flow/cli/experiment.py`:

```python
def resolver(workflow_name: str, experiment_config: ExperimentConfig) -> BaseWorkflowService:
    from tesseract_flow.workflows import YourWorkflow

    if normalized == "your_workflow":
        return YourWorkflow(config=workflow_config)
```

In `tesseract_flow/workflows/__init__.py`:

```python
from tesseract_flow.workflows.your_workflow import YourWorkflow

__all__ = [
    ...,
    "YourWorkflow",
]
```

---

## Common Mistakes

### ❌ WRONG: Using `from_test_config()` classmethod

```python
# NEVER DO THIS
@classmethod
def from_test_config(cls, test_config, experiment_config):
    return cls(...)
```

**Why Wrong:** This pattern doesn't exist in TesseractFlow. The framework calls `prepare_input()` instance method.

### ❌ WRONG: Passing temperature as direct parameter

```python
# NEVER DO THIS
strategy.generate(prompt, model=runtime.model, temperature=runtime.temperature)
```

**Why Wrong:** `temperature` must be passed inside `config` dict.

**✅ CORRECT:**
```python
parameters = {"temperature": runtime.temperature}
strategy.generate(prompt, model=runtime.model, config=parameters)
```

### ❌ WRONG: Using async LangGraph nodes

```python
# NEVER DO THIS
async def _execute_task(self, state: Dict[str, Any]) -> Dict[str, Any]:
    result = await strategy.generate(...)
```

**Why Wrong:** LangGraph `.invoke()` is synchronous. Nodes must be `def` functions that call `asyncio.run()` internally.

### ❌ WRONG: Not storing `_runtime` instance variable

```python
# NEVER DO THIS
def prepare_input(self, test_config, experiment_config):
    runtime = _RuntimeSettings(...)
    # Forgot to store it!
    return YourInput(...)
```

**Why Wrong:** `_initialize_state()` needs `self._runtime` to access settings during workflow execution.

### ❌ WRONG: Accessing `self.config.prompts`

```python
# NEVER DO THIS
prompt = self.config.prompts["task"]
```

**Why Wrong:** `WorkflowConfig` doesn't have a `prompts` attribute.

**✅ CORRECT:** Use `DEFAULT_PROMPTS` class attribute.

---

## Reference Examples

### Canonical Reference: `fiction_scene.py`

Location: `tesseract_flow/workflows/fiction_scene.py`

This is the gold standard implementation. Study it carefully.

### Validated Wave 2 Workflows

All 4 workflows successfully tested (2025-10-28):

1. **lore_expansion.py** → `/tmp/wave2_lore_test_v5.json`
   - 7 variables, 8 tests
   - Quality: 0.96-1.00, Utility: 0.69-0.75

2. **multi_task_benchmark.py** → `/tmp/wave2_thinking_styles_test.json`
   - 6 variables, 8 tests
   - Quality: 0.89-0.96, Utility: 0.69-0.77

3. **character_profile.py** → `/tmp/wave2_character_profile_test.json`
   - 6 variables, 8 tests
   - Quality: 0.97, Utility: 0.60-0.65

4. **multi_domain.py** → `/tmp/wave2_multi_domain_test.json`
   - 7 variables, 8 tests
   - Quality: 0.93-0.94, Utility: 0.62-0.69

---

## Testing Checklist

Before considering a workflow complete:

### 1. Validation Test (n=1)
```bash
source .env && \
.venv/bin/tesseract experiment run \
experiments/your_experiment.yaml \
--output /tmp/your_test.json 2>&1
```

**Expected:** Exit code 0, all 8 tests pass, no exceptions

### 2. Quick Check (5 seconds)
```bash
# Wait 5 seconds, check for errors
sleep 5
```

**Expected:** No KeyError, no TypeError, no AttributeError

### 3. Full Run (30+ seconds)
```bash
# Let it run for at least 30 seconds
sleep 30
```

**Expected:** LLM calls completing, quality scores generated

### 4. Analysis Test
```bash
.venv/bin/tesseract analyze main-effects /tmp/your_test.json
```

**Expected:**
- Variable contributions table displayed
- Optimal configuration shown
- Quality improvement calculated

### 5. Code Review Checklist

- [ ] Input model has `extra="allow"`
- [ ] Output model has `validate_assignment=True`
- [ ] Output implements `render_for_evaluation()`
- [ ] All string validators strip and check non-empty
- [ ] `_RuntimeSettings` dataclass defined
- [ ] `__init__()` sets `self._runtime = None`
- [ ] `prepare_input()` stores `self._runtime`
- [ ] All LangGraph nodes are synchronous `def` functions
- [ ] Temperature passed via `config` dict, not as parameter
- [ ] Workflow registered in `experiment.py`
- [ ] Workflow exported in `__init__.py`
- [ ] No references to `self.config.prompts` or `self.config.sample_code`

---

## Summary

### Key Takeaways

1. **Instance Method Pattern:** Use `prepare_input()`, NOT `from_test_config()`
2. **Runtime Storage:** ALWAYS store `self._runtime` in `prepare_input()`
3. **Temperature Passing:** Pass via `config={"temperature": ...}`, NOT as direct parameter
4. **Synchronous Nodes:** LangGraph nodes must be `def` (not `async def`)
5. **Validation:** Use Pydantic field validators for all string fields
6. **Reference Implementation:** Study `fiction_scene.py` as canonical example

### Common Error Pattern

```
KeyError: 'input' → Forgot to store self._runtime in prepare_input()
TypeError: unexpected keyword 'temperature' → Passed temp as direct param instead of in config dict
AttributeError: 'WorkflowConfig' has no 'prompts' → Use DEFAULT_PROMPTS class attribute
```

---

**Last Validated:** 2025-10-28 (Wave 2 workflows: lore_expansion, multi_task_benchmark, character_profile, multi_domain)
