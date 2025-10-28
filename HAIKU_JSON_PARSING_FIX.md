# Haiku Evaluator JSON Parsing Fix

**Date:** 2025-10-28
**Issue:** Haiku evaluator failing with "Evaluator response was not valid JSON"
**Status:** ✅ Fixed

## Problem Description

When using `openrouter/anthropic/claude-3.5-haiku` as the evaluator model, the RubricEvaluator was failing with:
```
EvaluationError: Evaluator response was not valid JSON
```

Despite the API call succeeding and authentication working correctly, the JSON parsing was failing.

## Root Cause

Claude Haiku (claude-3.5-haiku) sometimes adds preamble text before the JSON response, even when using `response_format={'type': 'json_object'}`. For example:

```
I'll carefully evaluate the output against the rubric:

{
  "clarity": {
    "score": 70,
    "reasoning": "Somewhat clear"
  },
  "accuracy": {
    "score": 85,
    "reasoning": "Mostly accurate"
  }
}
```

In contrast, DeepSeek-Chat returns pure JSON:
```
{
  "clarity": {
    "score": 80,
    "reasoning": "Clear output"
  }
}
```

The existing `_load_json()` method only handled:
1. Pure JSON
2. JSON wrapped in markdown code fences (` ```json ... ``` `)

But it did **not** handle preamble text before the JSON.

## Solution

Updated the `_load_json()` method in `/Users/markr/Documents/aiwriting/TesseractFlow/tesseract_flow/evaluation/rubric.py` to:

1. First try to parse as-is (handles pure JSON)
2. If that fails, search for the first `{` or `[` character in the string
3. Extract everything from that position onward
4. Try parsing again

This approach handles:
- ✅ Pure JSON (DeepSeek format)
- ✅ JSON with preamble text (Haiku format)
- ✅ JSON wrapped in markdown code fences
- ✅ Proper error handling for invalid JSON

## Code Changes

**File:** `tesseract_flow/evaluation/rubric.py`

**Method:** `_load_json()` (lines 308-345)

**Change:** Added fallback logic to extract JSON from preamble text:

```python
try:
    return json.loads(stripped)
except json.JSONDecodeError as exc:
    # Some models (like Haiku) add preamble text before JSON despite json_object mode
    # Try to extract JSON from the response by finding the first '{' or '['
    first_brace = stripped.find('{')
    first_bracket = stripped.find('[')

    # Determine which delimiter appears first (or if either exists)
    start_pos = -1
    if first_brace >= 0 and (first_bracket < 0 or first_brace < first_bracket):
        start_pos = first_brace
    elif first_bracket >= 0:
        start_pos = first_bracket

    if start_pos > 0:
        # Found JSON after some preamble text, extract it
        json_part = stripped[start_pos:]
        try:
            return json.loads(json_part)
        except json.JSONDecodeError:
            # Still failed, raise original error
            pass

    msg = "Evaluator response was not valid JSON."
    raise EvaluationError(msg) from exc
```

## Testing

### Unit Tests Added

Added 4 new tests to `tests/unit/test_rubric.py`:

1. `test_load_json_parses_pure_json()` - Pure JSON (DeepSeek format)
2. `test_load_json_parses_json_with_preamble()` - JSON with preamble (Haiku format)
3. `test_load_json_parses_markdown_fenced()` - JSON in code fences
4. `test_load_json_fails_on_invalid_json()` - Invalid JSON handling

All tests pass ✅

### End-to-End Testing

Tested with actual API calls to both models:

**Haiku:**
```
✅ Evaluation successful!
Overall Score: 0.78
Evaluator Model: openrouter/anthropic/claude-3.5-haiku
```

**DeepSeek-Chat:**
```
✅ DeepSeek evaluation successful!
Overall Score: 0.85
Evaluator Model: openrouter/deepseek/deepseek-chat
```

## Impact

- ✅ Haiku can now be used as an evaluator model
- ✅ Backward compatible with DeepSeek and other models
- ✅ More robust parsing for any LLM that adds preamble text
- ✅ No breaking changes to API or behavior

## Example Response Formats

### Haiku (with preamble)
```
I'll carefully evaluate the output against the rubric:

{
  "clarity": {
    "score": 70,
    "reasoning": "The output provides a basic overview..."
  }
}
```

### Haiku (pure JSON - sometimes)
```
{
  "clarity": {
    "score": 75,
    "reasoning": "The output provides a concise description..."
  }
}
```

### DeepSeek-Chat (always pure JSON)
```
{
  "clarity": {
    "score": 80,
    "reasoning": "The output is clear and understandable..."
  }
}
```

## Related Files

- `/Users/markr/Documents/aiwriting/TesseractFlow/tesseract_flow/evaluation/rubric.py` - Fixed JSON parsing
- `/Users/markr/Documents/aiwriting/TesseractFlow/tests/unit/test_rubric.py` - Added tests
- `/Users/markr/Documents/aiwriting/TesseractFlow/tesseract_flow/experiments/executor.py` - Uses RubricEvaluator

## Future Considerations

1. Monitor if other LLM providers have similar behavior
2. Consider adding logging to track when preamble extraction is used
3. Update prompt to be more explicit: "Respond with ONLY the JSON object, no preamble text"
4. Consider using structured output APIs if available for specific providers
