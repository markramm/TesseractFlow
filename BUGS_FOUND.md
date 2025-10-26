# Bugs Found During MVP Testing

**Date**: 2025-10-26
**Branch**: 001-mvp-optimizer
**Context**: Real-world testing with OpenRouter API

---

## BUG-001: Hardcoded Evaluator Model Requires Anthropic API Key

**Severity**: High
**Status**: FIXED ✅

**Problem:**
- `RubricEvaluator.DEFAULT_MODEL` was hardcoded to `"anthropic/claude-3.5-sonnet"`
- This required users to have Anthropic API keys even when using other providers
- Caused authentication errors when only OpenRouter keys were available

**Impact:**
- Users with only OpenRouter/OpenAI keys couldn't run experiments
- Not aligned with "Provider Agnostic" constitution principle

**Fix Applied:**
Changed DEFAULT_MODEL from `"anthropic/claude-3.5-sonnet"` to `"openrouter/deepseek/deepseek-chat"` in `tesseract_flow/evaluation/rubric.py:23`

**Better Solution for v2:**
- Add `evaluator_model` parameter to `workflow_config` in YAML
- Pass it through from ExperimentExecutor to RubricEvaluator
- Default to cheapest/fastest model (DeepSeek) but allow override

**Location**: `tesseract_flow/evaluation/rubric.py:23`

---

## BUG-002: Missing Generation Strategies in Example Configs

**Severity**: Medium
**Status**: NEEDS FIX 📋

**Problem:**
- Example config file uses `generation_strategy: "chain_of_thought"`
- Only `"standard"` strategy is registered in `GENERATION_STRATEGIES`
- Causes "Unknown generation strategy: chain_of_thought" error

**Files Affected:**
- `examples/code_review/experiment_config.yaml` (lines 15-17)
- `test_openrouter_config.yaml` (created during testing)
- `cheap_models_config.yaml` (created during testing)

**Impact:**
- Example configs don't work out of the box
- Users hit cryptic "Workflow execution failed" errors
- No clear error message about missing strategy

**Root Cause:**
Implementation only includes StandardStrategy, but documentation/examples reference chain_of_thought

**Fix Needed:**
1. **Short-term**: Update all example configs to only use `"standard"` strategy
2. **Long-term**:
   - Implement ChainOfThoughtStrategy class
   - Register it in GENERATION_STRATEGIES
   - Add better error messages when strategy not found

**Location**:
- `tesseract_flow/core/strategies.py:53-55`
- `examples/code_review/experiment_config.yaml`

---

## BUG-003: Unclear Error Messages for Workflow Failures

**Severity**: Low
**Status**: NEEDS FIX 📋

**Problem:**
- When workflow execution fails, error message is generic: "Workflow execution failed"
- No indication of root cause (missing strategy, API error, validation, etc.)
- Makes debugging difficult

**Example:**
```
01:33:37 ERROR [tesseract_flow.experiments.executor] Experiment cheap_models_test-20251026T053131 failed after 1/8 tests: Workflow execution failed.
```

**Impact:**
- Users can't diagnose issues without verbose logging
- Trial-and-error troubleshooting required

**Fix Needed:**
- Improve exception handling in ExperimentExecutor.run_single_test()
- Catch specific exception types and provide context:
  - ConfigurationError → "Invalid configuration: {detail}"
  - KeyError (strategy) → "Unknown generation strategy '{name}'. Available: {list}"
  - API errors → "LLM API call failed: {provider} {model} - {error}"
  - ValidationError → "Workflow output validation failed: {detail}"

**Location**: `tesseract_flow/experiments/executor.py:154-179`

---

##BUG-004: Example Config References Non-Existent evaluator_model Field

**Severity**: Low
**Status**: WORKAROUND APPLIED ⚠️

**Problem:**
- Added `evaluator_model: "openrouter/deepseek/deepseek-chat"` to workflow_config
- Field is accepted (because `extra="allow"`) but not actually used
- ExperimentExecutor doesn't pass it to RubricEvaluator

**Workaround:**
Changed DEFAULT_MODEL globally (BUG-001 fix)

**Proper Fix Needed:**
1. Add `evaluator_model: Optional[str] = None` to WorkflowConfig class
2. Pass it to ExperimentExecutor.__init__() or build_evaluator()
3. Use it in RubricEvaluator constructor: `RubricEvaluator(model=evaluator_model or DEFAULT_MODEL)`

**Locations**:
- `tesseract_flow/core/config.py:78-93` (WorkflowConfig)
- `tesseract_flow/cli/experiment.py:455-460` (build_evaluator)
- `tesseract_flow/experiments/executor.py:106-116` (evaluator usage)

---

## Testing Notes

**What Worked:**
- ✅ L8 Taguchi array generation
- ✅ Real OpenRouter API integration
- ✅ DeepSeek model calls (ultra-cheap, ~$0.00 per test)
- ✅ RubricEvaluator with LLM-as-judge
- ✅ Quality scoring (clarity, accuracy, actionability dimensions)
- ✅ Response caching for reproducibility
- ✅ Utility calculation and normalization
- ✅ Experiment resume functionality
- ✅ Progress tracking and JSON persistence

**What Needs Work:**
- ❌ Chain-of-thought strategy (not implemented)
- ❌ Error messages (too generic)
- ❌ Example configs (use non-existent features)
- ⚠️ Evaluator model configuration (not wired up)

---

## Recommended Priorities for Bug Fixes

1. **P0** (Blocking): ~~BUG-001~~ (FIXED)
2. **P1** (High): BUG-002 - Fix example configs and implement missing strategies
3. **P2** (Medium): BUG-004 - Wire up evaluator_model config parameter
4. **P3** (Low): BUG-003 - Improve error messages

---

## Next Steps

1. Commit BUG-001 fix (DEFAULT_MODEL change)
2. Create spec for BUG-002 (generation strategies)
3. Update all example configs to use only "standard" strategy
4. Run complete L8 experiment to validate end-to-end flow
5. Generate main effects analysis and Pareto chart
