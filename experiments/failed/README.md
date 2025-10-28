# Failed Experiments

This folder contains experiment configurations that produced invalid or biased results due to methodological issues.

## wave2_temperature_mapping.yaml

**Issue**: Rubric bias causing confounded results

**Problem**: The experiment attempted to test temperature effects across two task domains (creative_writing vs data_extraction) using a single rubric. The rubric criteria explicitly referenced task-appropriate behavior:

- "Temperature and sampling settings appropriate for **the task type**" (30% weight)
- "Appropriate level of randomness - **creative when needed, precise when required**" (25% weight)
- "Right balance between **creative exploration and factual accuracy** for task" (15% weight)

**Result**: The evaluator learned to prefer `data_extraction` tasks because they scored higher on "precision" criteria, creating a 36.4% main effect for `task_domain` that perfectly mirrored the 36.5% effect for `temperature=0.3`. These variables were **confounded** - impossible to tell if temperature matters or if the rubric simply prefers analytical tasks.

**Analysis**:
- n=1 results showed: temperature (36.5%), task_domain (36.4%)
- Nearly identical contributions suggest rubric bias, not real effects
- Running n=5 would just replicate the bias 5 times

**Lesson Learned**: Cross-domain experiments require either:
1. Domain-specific rubrics (separate evaluation criteria per task type)
2. Domain-agnostic rubrics (criteria that apply equally to all tasks)

**Status**: Invalid - Do not use for cross-experiment analysis

**Date**: 2025-10-28
