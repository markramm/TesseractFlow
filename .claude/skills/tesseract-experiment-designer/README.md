# TesseractFlow Experiment Designer Skill

**Version**: 1.0.0
**Created**: 2025-10-26
**Status**: Ready to use ✅

## Overview

This Claude Skill helps you design optimal TesseractFlow experiments using Taguchi Design of Experiments (DOE) methodology. It combines expert knowledge of model capabilities, costs, and benchmarks to recommend:

1. **Best-Guess Solutions**: Single configuration most likely to meet your needs
2. **Exploratory L8 Experiments**: Systematic testing to fill knowledge gaps and validate assumptions

## Quick Start

Simply invoke the skill in your Claude Code conversation:

```
/tesseract-experiment-designer
```

Then describe your workflow needs. The skill will guide you through experiment design.

## What This Skill Does

### 1. Gathers Requirements
Asks clarifying questions about:
- Workflow type (code review, content generation, analysis, etc.)
- Quality bar (production-ready, good-enough, experimental)
- Budget constraints (tight, moderate, flexible)
- Timeframe (immediate, can iterate, long-term)
- Known gaps (what you don't know yet)

### 2. Recommends Best-Guess Configuration
Provides a single optimal configuration with:
- Model selection (DeepSeek, Haiku 4.5, Sonnet 4.5)
- Temperature setting (0.0-1.0 based on task type)
- Context size (file_only, full_module)
- Generation strategy (standard, chain-of-thought, few-shot)
- Justification based on benchmarks and costs

### 3. Designs Exploratory L8 Experiment
Creates complete YAML configuration that:
- Tests 4 key variables in 8 experiments
- Includes your best-guess as one configuration
- Explores alternatives to validate assumptions
- Provides clear cost estimates

### 4. Estimates Costs
Transparent budget planning:
- Per-test costs
- Total L8 experiment cost
- Model comparison (e.g., DeepSeek vs. Haiku 4.5)
- Recommended baseline: **$0.10 per L8** (DeepSeek + Haiku 4.5 evaluation)

### 5. Explains Expected Outcomes
For each variable tested, explains:
- What you'll learn
- How it impacts quality/cost/speed
- Next steps based on results

## Knowledge Base

This skill has access to comprehensive model data:

### Model Cost Reference
- **Ultra-Low**: DeepSeek V3.1 ($0.69/M tokens)
- **Low**: Gemini 2.5 Flash ($1.40/M tokens)
- **Medium**: Claude Haiku 4.5 ($3.00/M tokens) ⭐
- **High**: Claude Sonnet 4.5 ($9.00/M tokens)
- **Premium**: GPT-5 Pro ($67.50/M tokens)

See `docs/openrouter-model-costs.md` for complete pricing.

### Model Capability Reference
- **Coding**: Claude Sonnet 4.5 (95%+ accuracy)
- **Speed**: Claude Haiku 4.5 (3x faster) ⭐
- **Reasoning**: DeepSeek R1 (specialized)
- **Long Context**: Gemini 2.5 Flash (1M tokens)

See `docs/openrouter-model-capabilities.md` for benchmarks.

## Example Workflows

### Workflow 1: Cost-Sensitive Code Review

**Your Input**: "I need a code review workflow that minimizes cost."

**Skill Output**:
- **Best-Guess**: DeepSeek V3.1 @ temp 0.5 with standard prompting
- **L8 Design**: Test DeepSeek vs. Haiku 4.5 to validate if premium needed
- **Cost**: $0.04 - $0.10 per L8
- **Justification**: DeepSeek provides competitive quality for 77% cost savings

### Workflow 2: Production-Quality Content Generation

**Your Input**: "I need production-ready blog post generation."

**Skill Output**:
- **Best-Guess**: Claude Sonnet 4.5 @ temp 0.7 with chain-of-thought
- **L8 Design**: Test Haiku 4.5 vs. Sonnet 4.5 to validate if premium quality needed
- **Cost**: $0.35 per L8
- **Justification**: State-of-the-art benchmarks, proven production quality

### Workflow 3: Fast-Iteration Exploration

**Your Input**: "Not sure which model works best, want to try several."

**Skill Output**:
- **Best-Guess**: Claude Haiku 4.5 (safe middle ground)
- **L8 Design**: Wide range - DeepSeek, Haiku 4.5, Sonnet 4.5
- **Cost**: $0.20-0.35 depending on config
- **Justification**: Experiment reveals which tier is sufficient for your use case

## File Structure

```
.claude/skills/tesseract-experiment-designer/
├── SKILL.md                          # Main skill definition (9.8 KB)
├── README.md                         # This file
└── references/
    ├── experiment-template.yaml      # Ready-to-use config template
    └── model-quick-reference.md      # Quick lookup tables
```

## Reference Files

### Quick Reference Tables
See `references/model-quick-reference.md` for:
- Model tier comparison table
- Temperature cheat sheet
- L8 cost estimates
- Common variable pairs
- Decision matrix

### Experiment Template
See `references/experiment-template.yaml` for:
- Complete YAML template
- Detailed variable explanations
- Cost estimates by model pair
- Workflow-specific examples

## Advanced Features

### Scenario Handling

The skill provides specialized guidance for:

1. **Cost-Critical Budget**: DeepSeek-only optimization
2. **Production-Quality Required**: Sonnet 4.5 validation
3. **Unknown Task Performance**: Wide model range exploration
4. **Speed-Critical Application**: Haiku 4.5 latency optimization

### Knowledge Gap Analysis

Helps identify what you don't know:
- "Does higher temperature improve output?" → Test temp variable
- "Is expensive model worth the cost?" → Test model with cost tracking
- "Does more context help?" → Test context_size variable
- "Do reasoning strategies improve quality?" → Test generation_strategy

## Best Practices

1. **Start Simple**: Don't test everything at once
2. **Iterate**: Run L8, analyze, refine, repeat
3. **Track Knowledge**: Document findings for future experiments
4. **Balance Exploration/Exploitation**: Mix safe choices with unknowns
5. **Consider Budget**: Small experiments allow more iterations

## Success Criteria

A well-designed experiment should:

✅ Have one configuration matching your best-guess need
✅ Explore 2-4 key unknowns systematically
✅ Fit within budget constraints
✅ Provide actionable insights regardless of results
✅ Enable clear next-step decisions

## Support

For issues or questions:
1. Check the main TesseractFlow documentation
2. Review the knowledge base docs:
   - `docs/openrouter-model-costs.md`
   - `docs/openrouter-model-capabilities.md`
3. File an issue in the TesseractFlow repository

## Version History

- **1.0.0** (2025-10-26): Initial release
  - Core experiment design process
  - Model cost/capability knowledge base
  - 4-variable L8 template
  - Advanced scenario handling
