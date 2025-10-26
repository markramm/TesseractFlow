# OpenRouter Model Cost Reference

**Last Updated**: 2025-10-26
**Source**: OpenRouter API v1 + Market Research

This document provides pricing information for models available via OpenRouter, organized by cost tier to help with experiment design and budget planning.

---

## Cost Tiers Overview

Models are categorized into cost tiers based on their pricing per million tokens (input + output average):

- **Free Tier**: $0.00/M tokens
- **Ultra-Low Cost**: < $0.50/M tokens
- **Low Cost**: $0.50 - $2.00/M tokens
- **Medium Cost**: $2.00 - $10.00/M tokens
- **High Cost**: $10.00 - $50.00/M tokens
- **Premium**: > $50.00/M tokens

---

## Ultra-Low Cost Models (< $0.50/M tokens)

### DeepSeek V3.1 (671B parameters)
- **Model ID**: `openrouter/deepseek/deepseek-chat`
- **Pricing**:
  - Input: $0.27/M tokens
  - Output: $1.10/M tokens
  - Average: ~$0.69/M tokens
- **Context Window**: 131,072 tokens (128K)
- **Description**: Large hybrid reasoning model with 671B total parameters, 37B active
- **Best For**: Cost-effective reasoning tasks, code generation
- **Latency**: Medium (larger model, slower inference)

### Gemini 2.5 Flash Preview
- **Model ID**: `openrouter/google/gemini-2.5-flash-preview`
- **Pricing**:
  - Input: $0.30/M tokens
  - Output: $2.50/M tokens
  - Average: ~$1.40/M tokens
- **Context Window**: 1,048,576 tokens (1M)
- **Description**: Google's fast multimodal model with built-in thinking capabilities
- **Best For**: Long-context tasks, multimodal processing
- **Latency**: Low (optimized for speed)

---

## Low Cost Models ($0.50 - $2.00/M tokens)

### Qwen3 Max
- **Model ID**: `openrouter/qwen/qwen-3-max`
- **Pricing**:
  - Input: $1.20/M tokens
  - Output: $6.00/M tokens
  - Average: ~$3.60/M tokens
- **Context Window**: 256,000 tokens
- **Description**: Alibaba's flagship model with strong multilingual capabilities
- **Best For**: Multilingual tasks, general-purpose reasoning

---

## Medium Cost Models ($2.00 - $10.00/M tokens)

### Claude Haiku 4.5 ⭐ **RECOMMENDED FOR EVALUATION**
- **Model ID**: `openrouter/anthropic/claude-haiku-4.5`
- **Pricing**:
  - Input: $1.00/M tokens
  - Output: $5.00/M tokens
  - Average: ~$3.00/M tokens
- **Context Window**: 200,000 tokens
- **Description**: Fastest Claude model, matches Sonnet 4 on coding/reasoning
- **Best For**: Evaluation, code review, fast iteration
- **Latency**: Very Low (optimized for speed)
- **Optimal Temperature**: 0.6-0.8 for quality writing
- **Special**: **3x faster than DeepSeek with similar quality**

---

## High Cost Models ($10.00 - $50.00/M tokens)

### Claude Sonnet 4.5
- **Model ID**: `openrouter/anthropic/claude-sonnet-4.5`
- **Pricing**:
  - Input: $3.00/M tokens
  - Output: $15.00/M tokens
  - Average: ~$9.00/M tokens
- **Context Window**: 1,000,000 tokens (1M)
- **Description**: Optimized for real-world agents and coding workflows
- **Best For**: Complex reasoning, agentic workflows, production code
- **Latency**: Low-Medium
- **Benchmarks**: State-of-the-art on SWE-bench, TAU-bench

---

## Premium Models (> $50.00/M tokens)

### GPT-5 Pro
- **Model ID**: `openrouter/openai/gpt-5-pro`
- **Pricing**:
  - Input: $15.00/M tokens
  - Output: $120.00/M tokens
  - Average: ~$67.50/M tokens
- **Context Window**: 400,000 tokens
- **Description**: OpenAI's latest flagship model
- **Best For**: Highest-stakes production use cases
- **Note**: 100x more expensive than DeepSeek, 22x more than Haiku 4.5

---

## Cost Comparison Table

| Model | Input ($/M) | Output ($/M) | Avg ($/M) | Context (K) | Speed Tier |
|-------|------------|--------------|-----------|-------------|------------|
| DeepSeek V3.1 | $0.27 | $1.10 | $0.69 | 128 | Medium |
| Gemini 2.5 Flash | $0.30 | $2.50 | $1.40 | 1,048 | Fast |
| Claude Haiku 4.5 | $1.00 | $5.00 | $3.00 | 200 | Fastest |
| Qwen3 Max | $1.20 | $6.00 | $3.60 | 256 | Medium |
| Claude Sonnet 4.5 | $3.00 | $15.00 | $9.00 | 1,000 | Fast |
| GPT-5 Pro | $15.00 | $120.00 | $67.50 | 400 | Medium |

---

## Experiment Design Recommendations

### Budget-Conscious Experiments
**Models**: DeepSeek V3.1, Gemini 2.5 Flash
**Use Case**: Early-stage exploration, high iteration count
**Expected Cost**: < $0.10 per 100K tokens

### Balanced Performance/Cost
**Models**: Claude Haiku 4.5, Qwen3 Max
**Use Case**: Production-ready evaluation, moderate quality needs
**Expected Cost**: $0.30 - $0.50 per 100K tokens

### Premium Quality
**Models**: Claude Sonnet 4.5, GPT-5 Pro
**Use Case**: Final validation, production deployment
**Expected Cost**: $1.00 - $7.00 per 100K tokens

---

## TesseractFlow Experiment Cost Estimates

### Taguchi L8 Experiment (8 tests)

Assuming average test uses:
- **Workflow Generation**: 2,000 input + 1,000 output tokens
- **Evaluation**: 3,000 input + 500 output tokens
- **Total per test**: ~6,500 tokens

| Model Combination | Cost per L8 | Notes |
|------------------|-------------|-------|
| DeepSeek + DeepSeek | $0.04 | Ultra budget |
| DeepSeek + Haiku 4.5 | $0.10 | Recommended baseline |
| Haiku 4.5 + Haiku 4.5 | $0.16 | Fast iteration |
| Sonnet 4.5 + Haiku 4.5 | $0.35 | Production quality |
| Sonnet 4.5 + Sonnet 4.5 | $0.47 | Premium validation |

---

## Free Tier Information

### Rate Limits
- **No credits**: 50 requests/day total across all free models
- **With $10+ credits**: 1,000 requests/day per free model

### Free Models Available
- DeepSeek R1 Free
- Mistral variants (free tier)
- Llama 3.3 70B (some providers)
- Google Gemini Flash (limited)

### BYOK (Bring Your Own Key)
- **First 1M requests/month**: Free
- **Additional requests**: 5% fee
- **Benefit**: Direct provider pricing, no markup

---

## Pricing Notes

1. **Pricing Volatility**: Model costs can change. Check OpenRouter API for current rates.
2. **Platform Fee**: OpenRouter charges a small platform fee on credit purchases but never marks up provider pricing.
3. **Reasoning Tokens**: Some models (e.g., DeepSeek R1) charge separately for reasoning tokens.
4. **Image Processing**: Multimodal models may charge per image or per request.
5. **Batch Discounts**: Some providers offer discounts for high-volume usage.

---

## API Access

**Models API Endpoint**: `https://openrouter.ai/api/v1/models`

**Example Request**:
```bash
curl https://openrouter.ai/api/v1/models \
  -H "Authorization: Bearer $OPENROUTER_API_KEY"
```

**LiteLLM Format**: Prefix model IDs with `openrouter/` (e.g., `openrouter/deepseek/deepseek-chat`)

---

## References

- OpenRouter Models Browser: https://openrouter.ai/models
- OpenRouter Documentation: https://openrouter.ai/docs
- Pricing Calculator: https://invertedstone.com/calculators/openrouter-pricing
- Model Rankings: https://openrouter.ai/rankings
