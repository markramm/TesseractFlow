# Model Quick Reference

**Quick lookup for experiment design**

## Model Tiers

| Tier | Model | Cost/M | Speed | Quality | Best For |
|------|-------|--------|-------|---------|----------|
| Budget | DeepSeek V3.1 | $0.69 | Medium | Good | Cost-sensitive workflows |
| Balanced | Claude Haiku 4.5 | $3.00 | Fastest | Excellent | Most use cases ⭐ |
| Premium | Claude Sonnet 4.5 | $9.00 | Fast | Best | Production quality |

## Temperature Cheat Sheet

| Task Type | Temperature | Examples |
|-----------|-------------|----------|
| Deterministic | 0.0-0.4 | Code gen, data extraction, JSON output |
| Balanced | 0.5-0.7 | Technical writing, Q&A, analysis |
| Creative | 0.8-1.0 | Storytelling, brainstorming |

## L8 Cost Estimates (per 6.5K tokens)

| Workflow + Eval | Cost |
|----------------|------|
| DeepSeek + DeepSeek | $0.04 |
| **DeepSeek + Haiku 4.5** | **$0.10** ⭐ |
| Haiku + Haiku | $0.16 |
| Sonnet + Haiku | $0.35 |

⭐ = Recommended baseline

## Common Variable Pairs

### Budget-Conscious
```yaml
model:
  level_1: "openrouter/deepseek/deepseek-chat"
  level_2: "openrouter/anthropic/claude-haiku-4.5"
```

### Quality-Focused
```yaml
model:
  level_1: "openrouter/anthropic/claude-haiku-4.5"
  level_2: "openrouter/anthropic/claude-sonnet-4.5"
```

### Standard Temperature
```yaml
temperature:
  level_1: 0.3  # Deterministic
  level_2: 0.7  # Creative
```

### Code-Focused Temperature
```yaml
temperature:
  level_1: 0.2  # Very deterministic
  level_2: 0.5  # Slightly varied
```

## Evaluation Recommendations

- **Standard**: Claude Haiku 4.5 @ temp 0.3
- **Budget**: DeepSeek V3.1 @ temp 0.3
- **Scale**: 0-100 points per dimension
- **Weights**: Based on task priority

## Decision Matrix

| Priority | Model Choice | Temperature | Expected Cost |
|----------|-------------|-------------|---------------|
| Speed | Haiku 4.5 | 0.3-0.6 | $0.16 |
| Cost | DeepSeek | 0.4-0.6 | $0.04 |
| Quality | Sonnet 4.5 | 0.3-0.5 | $0.47 |
| Balanced | Haiku 4.5 | 0.5-0.7 | $0.16 |
