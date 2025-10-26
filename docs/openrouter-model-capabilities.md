# OpenRouter Model Capabilities Guide

**Last Updated**: 2025-10-26
**Source**: OpenRouter Rankings, Benchmarks, Community Research

This document provides performance benchmarks, optimal settings, and use-case recommendations for models available via OpenRouter.

---

## Model Categories

Models are organized by their primary strengths:

1. **Coding & Development**
2. **Reasoning & Analysis**
3. **General Purpose**
4. **Speed-Optimized**
5. **Long Context**
6. **Multimodal**

---

## Top Performers by Category

### 🏆 Coding & Development

#### 1. Claude Sonnet 4.5 (Best Overall)
- **Benchmarks**:
  - SWE-bench Verified: State-of-the-art
  - TAU-bench: State-of-the-art
  - Coding Accuracy: 95%+
- **Optimal Settings**:
  - Temperature: 0.3-0.5 (deterministic code generation)
  - Top-p: 0.9
  - Max tokens: 4096-8192 for code gen
- **Best For**:
  - Production code generation
  - Complex refactoring
  - Architecture design
  - Front-end web development
- **Latency**: Low-Medium (acceptable for interactive coding)

#### 2. DeepSeek V3.1 (Best Value)
- **Benchmarks**:
  - Coding tasks: Competitive with much larger models
  - MMLU: 81% accuracy
- **Optimal Settings**:
  - Temperature: 0.4-0.6 (focused code)
  - Top-p: 0.95
- **Best For**:
  - Cost-effective code generation
  - Batch processing
  - Code review automation
- **Latency**: Medium (larger model, slower but thorough)

#### 3. Horizon Beta / Andromeda Alpha
- **Benchmarks**:
  - Coding Accuracy: 95.0% - 95.8%
  - Percentile Rank: 97th
- **Optimal Settings**:
  - Temperature: 0.3-0.7
- **Best For**:
  - Specialized coding tasks
  - High accuracy requirements

---

### 🧠 Reasoning & Analysis

#### 1. Claude Sonnet 4.5
- **Benchmarks**:
  - Complex reasoning: Frontier-level
  - Multi-step problem solving: Excellent
- **Optimal Settings**:
  - Temperature: 0.5-0.7 (balanced reasoning)
  - Chain-of-thought prompting: Highly effective
- **Best For**:
  - Strategic planning
  - Complex problem decomposition
  - Research analysis

#### 2. DeepSeek R1 (Specialized Reasoning)
- **Benchmarks**:
  - Math & logic: Strong performance
  - Reasoning tokens: Separate billing for thinking process
- **Optimal Settings**:
  - Temperature: 0.6-0.8 (focused reasoning)
  - Top-p: 0.95
- **Best For**:
  - Mathematical proofs
  - Logical deduction
  - Scientific reasoning
- **Note**: Uses separate reasoning token pool

#### 3. Horizon Beta (Ethics & Knowledge)
- **Benchmarks**:
  - General Knowledge: 100% accuracy
  - Ethics: 100% accuracy
  - Overall Rank: #1 in accuracy
- **Best For**:
  - Ethical analysis
  - Knowledge-intensive tasks
  - Factual accuracy

---

### 💬 General Purpose

#### 1. Claude Haiku 4.5 ⭐ **RECOMMENDED**
- **Benchmarks**:
  - Matches Sonnet 4 on many tasks
  - Quality/Speed ratio: Best in class
- **Optimal Settings**:
  - Temperature: 0.6-0.8 (quality writing)
  - Top-p: 0.9
  - Frequency penalty: 0.0-0.3
- **Best For**:
  - Content generation
  - Summarization
  - Question answering
  - Chat applications
  - **LLM-as-Judge evaluation**
- **Special**: **3x faster than competitors with similar quality**

#### 2. Mistral Small 3
- **Benchmarks**:
  - MMLU: 81% accuracy
  - Speed: 3x faster than Llama 3.3 70B
- **Optimal Settings**:
  - Temperature: 0.7-0.9 (creative tasks)
- **Best For**:
  - European language tasks
  - Cost-effective general use

---

### ⚡ Speed-Optimized

#### 1. Claude Haiku 4.5 (Fastest Quality Model)
- **Infrastructure**: Optimized for low latency
- **First Token Latency**: Very low
- **Use Case**: Interactive applications, real-time responses

#### 2. Gemini 2.5 Flash Preview
- **Infrastructure**: Google's optimized serving
- **Context Window**: 1M tokens (excellent for speed with context)
- **Use Case**: Long-context quick processing

#### 3. Groq / SambaNova Infrastructure
- **First Token Latency**: Lowest available
- **Use Case**: Streaming responses, chatbots
- **Note**: Provider-dependent, check availability

---

### 📚 Long Context

#### 1. Claude Sonnet 4.5 (1M tokens)
- **Context Window**: 1,000,000 tokens
- **Optimal for**: Code repositories, entire books, large datasets
- **Pricing**: Higher due to context size

#### 2. Gemini 2.5 Flash Preview (1M tokens)
- **Context Window**: 1,048,576 tokens
- **Optimal for**: Document analysis, long conversations
- **Advantage**: Lower cost per token

#### 3. Qwen3 Max (256K tokens)
- **Context Window**: 256,000 tokens
- **Optimal for**: Medium-length documents, extended conversations

---

### 🎨 Multimodal

#### 1. Gemini 2.5 Flash Preview
- **Capabilities**: Text, images, video, audio
- **Built-in thinking**: Internal reasoning capabilities
- **Use Case**: Multimodal analysis, content understanding

#### 2. Claude Sonnet 4.5
- **Capabilities**: Text + vision (images)
- **Use Case**: Image analysis, diagram interpretation, OCR

---

## Temperature Guidelines by Task

### Deterministic Tasks (Low Temperature: 0.0-0.4)
- Code generation
- Data extraction
- Structured output (JSON, YAML)
- Mathematical calculations
- Translation

**Recommended Models**: Claude Sonnet 4.5, DeepSeek V3.1

### Balanced Tasks (Medium Temperature: 0.5-0.7)
- Technical writing
- Code review
- Question answering
- Summarization
- Analysis

**Recommended Models**: Claude Haiku 4.5, Qwen3 Max

### Creative Tasks (High Temperature: 0.8-1.0)
- Creative writing
- Brainstorming
- Dialogue generation
- Story generation

**Recommended Models**: Claude Haiku 4.5, Mistral Small

---

## TesseractFlow Experiment Design Guide

### Workflow Generation Models

**Code Review Workflow**:
- **Production**: Claude Sonnet 4.5 (temp: 0.3-0.5)
- **Development**: Claude Haiku 4.5 (temp: 0.4-0.6)
- **Budget**: DeepSeek V3.1 (temp: 0.4-0.6)

**Content Generation Workflow**:
- **High Quality**: Claude Sonnet 4.5 (temp: 0.6-0.8)
- **Balanced**: Claude Haiku 4.5 (temp: 0.7-0.9)
- **Budget**: Gemini 2.5 Flash (temp: 0.7-0.9)

### Evaluation Models (LLM-as-Judge)

**Recommended**: Claude Haiku 4.5
- **Temperature**: 0.3 (consistent evaluation)
- **Reasoning**: Fast, cost-effective, high-quality judgments
- **Proven**: Used in production evaluation systems

**Alternative**: DeepSeek V3.1
- **Temperature**: 0.3
- **Reasoning**: Ultra low-cost for high-volume evaluation
- **Trade-off**: Slower inference

---

## Taguchi Variable Selection

### Model Variable (Level 1 vs Level 2)

**Recommended Pairs**:

1. **Cost-Optimized**:
   - Level 1: DeepSeek V3.1
   - Level 2: Claude Haiku 4.5
   - Rationale: Test budget vs. quality trade-off

2. **Quality-Optimized**:
   - Level 1: Claude Haiku 4.5
   - Level 2: Claude Sonnet 4.5
   - Rationale: Test speed vs. capability trade-off

3. **Balanced**:
   - Level 1: DeepSeek V3.1
   - Level 2: Claude Sonnet 4.5
   - Rationale: Maximum range exploration

### Temperature Variable

**Standard Range**:
- Level 1: 0.3 (deterministic)
- Level 2: 0.7 (creative)

**Code-Focused**:
- Level 1: 0.2 (very deterministic)
- Level 2: 0.5 (slightly varied)

**Creative-Focused**:
- Level 1: 0.6 (controlled)
- Level 2: 0.9 (very creative)

### Context Size Variable

**Recommended Levels**:
- Level 1: `file_only` (focused, fast)
- Level 2: `full_module` (comprehensive, slower)

**Rationale**: Tests information scope impact

### Generation Strategy Variable

**Recommended Levels**:
- Level 1: `standard` (direct prompting)
- Level 2: `chain_of_thought` (reasoning-based)

**Alternative**:
- Level 1: `standard`
- Level 2: `few_shot` (example-based)

---

## Benchmark Summary Table

| Model | MMLU | Coding | Speed | Context | Cost Rank |
|-------|------|--------|-------|---------|-----------|
| Claude Sonnet 4.5 | N/A | 95%+ ⭐ | Medium | 1M | High |
| Claude Haiku 4.5 | N/A | 95% | Fastest ⭐ | 200K | Low |
| DeepSeek V3.1 | 81% | Strong | Medium | 128K | Ultra-low ⭐ |
| Gemini 2.5 Flash | N/A | Good | Fast | 1M ⭐ | Ultra-low |
| Horizon Beta | 100% ⭐ | 95% | Fast | N/A | Medium |
| Qwen3 Max | N/A | Good | Medium | 256K | Low |

⭐ = Best in category

---

## Model Selection Decision Tree

```
START: What's your priority?

├─ COST →
│  ├─ Need quality? → Claude Haiku 4.5
│  └─ Maximum savings? → DeepSeek V3.1
│
├─ SPEED →
│  ├─ Need quality? → Claude Haiku 4.5 ⭐
│  └─ Just fast? → Gemini 2.5 Flash
│
├─ QUALITY →
│  ├─ Coding? → Claude Sonnet 4.5 ⭐
│  └─ General? → Claude Haiku 4.5
│
└─ CONTEXT →
   ├─ Very long (1M+)? → Gemini 2.5 Flash
   ├─ Long (1M)? → Claude Sonnet 4.5
   └─ Standard? → Claude Haiku 4.5
```

---

## Provider Infrastructure Notes

### Groq
- **Strength**: Lowest first-token latency
- **Use**: Real-time streaming applications
- **Limitation**: Limited model selection

### SambaNova
- **Strength**: Fast inference, good latency
- **Use**: Production deployments
- **Limitation**: Model availability varies

### TogetherAI
- **Strength**: Good performance/cost balance
- **Use**: Batch processing, high-volume tasks
- **Note**: Competitive with OpenRouter

---

## References

- OpenRouter Rankings: https://openrouter.ai/rankings
- Model Browser: https://openrouter.ai/models
- Benchable AI Model Database: https://benchable.ai
- Triplo AI Model Guide: https://documentation.triplo.ai/faq/open-router-models-and-its-strengths
- OpenRouter Documentation: https://openrouter.ai/docs
