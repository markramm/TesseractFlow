# TesseractFlow Iteration Patterns

**Date**: 2025-10-26
**Status**: Best Practices Guide
**Philosophy**: Lean LLM Optimization through Continuous Improvement

---

## Core Philosophy: Lean Iteration Over Perfectionism

> **"Get good enough results in 10 minutes for $0.40, ship fast, iterate based on real usage."**

TesseractFlow is not a one-shot optimizer - it's a **continuous improvement engine**. Run a $0.40 experiment every sprint, building on learnings from the previous iteration.

### The Lean Advantage

**Traditional Approach (Perfectionism):**
```
Spend 3 months optimizing everything up-front
→ Ship "perfect" solution
→ Discover users need something different
→ All optimization was wasted
```

**TesseractFlow Approach (Lean Iteration):**
```
Spend 10 minutes finding optimal architecture
→ Ship good enough solution
→ Gather real usage data
→ Next sprint: Run another $0.40 experiment
→ Continuously improve based on what users actually need
```

### The 80/20 Rule of LLM Optimization

```
First $0.40 (TesseractFlow L8):      Get 70% of optimal quality
Next $2 (DSPy optimization):          Get another 10% (80% total)
Next $10 (Agentic workflows):         Get another 5% (85% total)
Next $100 (RAG + re-ranking):         Get another 3% (88% total)
Next $1000 (Fine-tuning):             Get another 2% (90% total)
Next $10000 (RLHF):                   Get another 2% (92% total)
```

**TesseractFlow's sweet spot:** Get the first 70% for $0.40 in 10 minutes, then iterate based on what you learn from real users.

---

## The Five-Iteration Journey

Here's a typical progression from "initial idea" to "production-optimized" over 5 sprints:

### Iteration 1: Architecture Foundation ($0.40, Sprint 1)

**Goal:** Find the best high-level architecture

**What to test:**
```yaml
variables:
  - name: "model_tier"
    level_1: "budget"      # DeepSeek, Llama
    level_2: "premium"     # Sonnet, GPT-4

  - name: "context_strategy"
    level_1: "file_only"
    level_2: "full_module"

  - name: "workflow_architecture"
    level_1: "single_pass"
    level_2: "multi_step_agentic"

  - name: "prompting_strategy"
    level_1: "standard"
    level_2: "chain_of_thought"
```

**Example Results:**
- `model_tier`: 8% contribution (Premium slightly better, but expensive)
- `context_strategy`: **52% contribution** ← High impact!
- `workflow_architecture`: 25% contribution (Multi-step better)
- `prompting_strategy`: 15% contribution (Standard actually better)

**Decisions:**
- ✅ Use budget model (Haiku) - 8% impact not worth 5x cost
- ✅ Use full_module context - 52% impact, critical!
- ✅ Use multi_step workflow - 25% impact, worth the complexity
- ✅ Use standard prompting - Simpler and better

**Ship it:** 70% quality baseline

**Key Learning:** Context strategy matters most (52%) - focus next iteration there

---

### Iteration 2: Optimize High-Impact Variable ($0.40, Sprint 2)

**Goal:** Deep dive on the variable with highest contribution (context: 52%)

**What to test:**
```yaml
# Lock in decisions from Iteration 1: haiku, multi_step, standard
# Vary: 4 different context strategies

variables:
  - name: "context_scope"
    level_1: "immediate_imports"
    level_2: "transitive_dependencies"

  - name: "context_format"
    level_1: "raw_code"
    level_2: "annotated_with_types"

  - name: "context_summarization"
    level_1: "no_summary"
    level_2: "llm_summary"

  - name: "context_metadata"
    level_1: "no_metadata"
    level_2: "with_git_history"
```

**Example Results:**
- `context_scope`: **38% contribution** (Transitive dependencies critical!)
- `context_format`: **35% contribution** (Type annotations help a lot)
- `context_summarization`: 22% contribution (Summaries help with large files)
- `context_metadata`: 5% contribution (Git history doesn't help)

**Decisions:**
- ✅ Use transitive dependencies
- ✅ Annotate with type information
- ✅ Add LLM summarization for large files
- ❌ Skip git history metadata

**Ship it:** 70% → 78% quality (+8% improvement)

**Key Learning:** Type annotations and dependency tracking are critical for quality

---

### Iteration 3: Address User Pain Points ($0.40, Sprint 4)

**Goal:** Fix the biggest complaint from users (slow responses on large codebases)

**What to test:**
```yaml
# Hypothesis: Progressive discovery (MCP, RAG) could improve both speed AND quality
# Test: Different progressive discovery mechanisms

variables:
  - name: "discovery_mechanism"
    level_1: "static_context"      # Load everything up-front
    level_2: "mcp_tools"            # Use MCP for on-demand context

  - name: "tool_availability"
    level_1: "read_only"
    level_2: "read_and_search"      # Add search/grep tools

  - name: "caching_strategy"
    level_1: "no_cache"
    level_2: "cache_embeddings"

  - name: "initial_context"
    level_1: "minimal"              # Just target file
    level_2: "predictive"           # Pre-load likely dependencies
```

**Example Results:**
- `discovery_mechanism`: **45% contribution** (MCP is game-changer!)
- `tool_availability`: **28% contribution** (Search tools help quality)
- `caching_strategy`: 20% contribution (Embeddings improve speed)
- `initial_context`: 7% contribution (Predictive pre-loading doesn't help)

**Decisions:**
- ✅ Switch to MCP tools for progressive discovery
- ✅ Add search/grep capabilities
- ✅ Cache embeddings for faster retrieval
- ❌ Skip predictive pre-loading (complexity not worth 7%)

**Ship it:** 78% → 80% quality (+2%), **6x latency improvement** (30s → 5s)

**Key Learning:** Progressive discovery solves both quality AND performance problems

---

### Iteration 4: Prompt Refinement ($0.40, Sprint 6)

**Goal:** Optimize prompts now that architecture is stable

**What to test:**
```yaml
# Lock in: haiku, MCP tools, search, embeddings
# Vary: 4 prompt strategies

variables:
  - name: "task_framing"
    level_1: "imperative"           # "Review this code for issues"
    level_2: "goal_oriented"        # "Your goal is to improve code quality"

  - name: "tool_usage_prompt"
    level_1: "implicit"             # Model decides when to use tools
    level_2: "explicit"             # "Use search when you need context"

  - name: "output_format"
    level_1: "freeform_markdown"
    level_2: "structured_json"

  - name: "context_instruction"
    level_1: "brief"                # "Here's the code:"
    level_2: "detailed"             # "Below is the target file..."
```

**Example Results:**
- `task_framing`: 8% contribution (Minimal difference)
- `tool_usage_prompt`: **42% contribution** (Explicit instructions critical!)
- `output_format`: **35% contribution** (JSON structure helps downstream processing)
- `context_instruction`: 15% contribution (Detailed helps)

**Decisions:**
- ✅ Add explicit tool usage instructions
- ✅ Switch to structured JSON output
- ✅ Use detailed context descriptions
- ⚖️ Keep imperative framing (8% not worth changing)

**Ship it:** 80% → 85% quality (+5% improvement)

**Key Learning:** Explicit tool instructions are critical for agentic workflows

---

### Iteration 5: Cost Optimization ($0.40, Sprint 8)

**Goal:** Reduce costs while maintaining quality

**What to test:**
```yaml
# Quality is great (85%), but can we reduce cost?
# Test: Different cost/quality tradeoffs

variables:
  - name: "model_for_analysis"
    level_1: "haiku"                # Current: $3/M
    level_2: "deepseek"             # Cheaper: $0.69/M

  - name: "model_for_summaries"
    level_1: "same_as_analysis"     # Haiku for everything
    level_2: "cheaper_model"        # DeepSeek for summaries only

  - name: "embedding_model"
    level_1: "openai_ada"           # $0.10/M tokens
    level_2: "free_local"           # Free local embeddings

  - name: "cache_aggressiveness"
    level_1: "conservative"         # Cache 1 day
    level_2: "aggressive"           # Cache 7 days
```

**Example Results:**
- `model_for_analysis`: 15% contribution (Haiku still better for main task)
- `model_for_summaries`: **5% contribution** (DeepSeek fine for summaries!)
- `embedding_model`: 2% contribution (Local embeddings work great)
- `cache_aggressiveness`: 8% contribution (Aggressive caching helps)

**Decisions:**
- ✅ Keep Haiku for main analysis
- ✅ Use DeepSeek for context summaries
- ✅ Switch to local embeddings
- ✅ Enable aggressive caching

**Ship it:** 85% → 82% quality (-3%), **35% cost reduction**

**Key Learning:** Can mix-and-match model tiers for different sub-tasks

---

## Summary: Five-Iteration Results

| Sprint | Focus | Cost | Quality | Other Metrics |
|--------|-------|------|---------|---------------|
| **1** | Architecture foundation | $0.40 | 70% | Baseline |
| **2** | Context optimization | $0.40 | 78% | +8% quality |
| **3** | Progressive discovery | $0.40 | 80% | +2% quality, 6x faster |
| **4** | Prompt refinement | $0.40 | 85% | +5% quality |
| **5** | Cost optimization | $0.40 | 82% | -3% quality, 35% cheaper |

**Total Investment:** 5 × $0.40 = **$2.00**
**Total Experiment Time:** 5 × 10 minutes = **50 minutes**
**Total Calendar Time:** ~10 weeks (with user feedback cycles)
**Final Result:** 82% quality, 35% cost savings, 6x latency improvement

**Alternative (DSPy up-front):** Spend $5 and 3 hours, get 85% quality for one specific configuration, then start over when requirements change.

---

## Core Iteration Patterns

### Pattern 1: "Start Broad, Then Narrow"

**When to use:** Beginning a new project or feature

**Process:**
1. **Sprint 1:** Test 4 different high-level architectures (broad exploration)
2. **Sprint 2:** Deep dive on the winning architecture (narrow focus)
3. **Sprint 3:** Optimize the highest-contribution variable (narrow focus)
4. **Sprint 4:** Re-test architecture with optimizations (validation)

**Example:**
```
Sprint 1: Test model_tier, context, workflow, prompting
  → Result: context matters most (52%)

Sprint 2: Test 4 context strategies
  → Result: type_annotations matter most (35%)

Sprint 3: Test 4 type annotation formats
  → Result: inline_types best

Sprint 4: Re-test original 4 variables with optimized context
  → Validate: context still matters most, but contribution now 45% (optimized!)
```

---

### Pattern 2: "Follow the Main Effects"

**When to use:** Systematic optimization over multiple sprints

**Process:**
1. Run L8 experiment
2. Sort variables by contribution percentage
3. Next sprint: Deep dive on highest contributor
4. Lock in winning choice
5. Repeat with next highest contributor

**Example:**
```
Sprint 1 Results:
- context: 52% ← Highest
- workflow: 25%
- prompting: 15%
- model: 8%

Sprint 2: Optimize context (52% contribution)
  → Improvement: 70% → 78% quality

Sprint 3: Optimize workflow (25% contribution)
  → Improvement: 78% → 81% quality

Sprint 4: Optimize prompting (15% contribution)
  → Improvement: 81% → 83% quality

Sprint 5: Skip model (8% not worth optimization effort)
```

---

### Pattern 3: "User Feedback First"

**When to use:** Responding to production usage and user complaints

**Process:**
1. Ship current best configuration
2. Gather usage data for 1-2 weeks
3. Identify biggest user complaint or pain point
4. Design L8 experiment to address that specific issue
5. Deploy improvement
6. Measure impact
7. Repeat

**Example:**
```
Week 1-2: Users complain "reviews are slow on large files"
  → Hypothesis: Progressive discovery (MCP) could help
  → Experiment: Test MCP vs static, different caching strategies
  → Result: MCP reduces latency 6x!

Week 3-4: Users complain "tool hallucinations - wrong files searched"
  → Hypothesis: Explicit tool instructions needed
  → Experiment: Test implicit vs explicit tool prompts
  → Result: Explicit instructions reduce hallucinations 40%

Week 5-6: Users love it, but costs are high
  → Hypothesis: Can use cheaper models for some sub-tasks
  → Experiment: Test model tiers for different components
  → Result: 35% cost reduction with minimal quality drop
```

---

### Pattern 4: "Pareto Frontier Walk"

**When to use:** Exploring quality/cost/latency tradeoffs

**Process:**
1. **Sprint 1:** Optimize for quality only (ignore cost and latency)
2. **Sprint 2:** Add cost constraint (quality > 80%, minimize cost)
3. **Sprint 3:** Add latency constraint (quality > 80%, cost < $X, minimize latency)
4. **Sprint 4:** Find optimal tradeoff point for your use case

**Example:**
```
Sprint 1: Pure quality optimization
  → Result: 90% quality, $0.10/request, 30s latency

Sprint 2: Add cost constraint (quality > 80%, minimize cost)
  → Test cheaper models, caching, smaller context
  → Result: 82% quality, $0.02/request, 35s latency

Sprint 3: Add latency constraint (quality > 80%, cost < $0.03, minimize latency)
  → Test MCP, streaming, parallel execution
  → Result: 81% quality, $0.025/request, 8s latency

Sprint 4: Fine-tune the sweet spot
  → Test variations around 81% quality / $0.025 / 8s
  → Result: 83% quality, $0.028/request, 6s latency (optimal!)
```

---

### Pattern 5: "Progressive Refinement"

**When to use:** Long-term continuous improvement (ongoing)

**Process:**
Each iteration builds on learnings from the previous one, progressively refining different aspects:

1. **Foundation:** Architecture-level choices
2. **Depth:** Optimize high-impact variables
3. **Performance:** Address speed/latency issues
4. **Quality:** Prompt and workflow refinement
5. **Efficiency:** Cost optimization
6. **Edge Cases:** Handle corner cases and failures

**Example: Code Review Feature Evolution**

```
Month 1 - Foundation:
  Sprint 1: Find architecture (model, context, workflow, prompting)
  Sprint 2: Optimize context strategy (biggest contributor)

Month 2 - Performance:
  Sprint 3: Add progressive discovery (MCP) for speed
  Sprint 4: Optimize caching and tool usage

Month 3 - Quality:
  Sprint 5: Refine prompts and instructions
  Sprint 6: Add structured output (JSON schema)

Month 4 - Efficiency:
  Sprint 7: Cost optimization (cheaper models for sub-tasks)
  Sprint 8: Optimize cache hit rates

Month 5 - Edge Cases:
  Sprint 9: Handle very large files (>10k lines)
  Sprint 10: Handle unfamiliar languages/frameworks

Result: 85% quality, $0.02/review, 5s latency, handles edge cases
```

---

### Pattern 6: "A/B Test in Production"

**When to use:** Validating hypotheses with real user data

**Process:**
1. Run L8 experiment to identify promising configuration
2. Deploy winning config to 50% of users (A/B test)
3. Compare metrics: quality, cost, latency, user satisfaction
4. If better: Roll out to 100%
5. If not: Investigate why lab results didn't match production

**Example:**
```
Lab Experiment: MCP tools improve quality by 5%
A/B Test:
  - Group A (50%): Static context (baseline)
  - Group B (50%): MCP tools

Results after 1 week:
  - Quality: +3% (lower than lab, but still positive)
  - Latency: -20% (better than expected!)
  - User satisfaction: +15% (users love faster responses)

Decision: Roll out MCP to 100% (latency improvement worth quality tradeoff)

Learning: Latency matters more to users than we thought!
  → Next experiment: Focus on further latency optimizations
```

---

## Iteration Types by Goal

### Goal: Maximize Quality

**Experiment Design:**
```yaml
# Test quality-focused variables
variables:
  - name: "model_tier"
    level_1: "mid_tier"    # e.g., Haiku
    level_2: "premium"     # e.g., Sonnet, GPT-4

  - name: "context_richness"
    level_1: "minimal"
    level_2: "comprehensive"

  - name: "reasoning_depth"
    level_1: "single_pass"
    level_2: "multi_step_reflection"

  - name: "validation"
    level_1: "no_validation"
    level_2: "self_validation"

# Utility weights favor quality
utility_weights:
  quality: 1.0
  cost: 0.0
  time: 0.0
```

---

### Goal: Minimize Cost

**Experiment Design:**
```yaml
# Test cost-reduction variables
variables:
  - name: "model_tier"
    level_1: "budget"      # e.g., DeepSeek, Llama
    level_2: "mid_tier"    # e.g., Haiku

  - name: "context_size"
    level_1: "minimal"
    level_2: "moderate"

  - name: "caching"
    level_1: "conservative"
    level_2: "aggressive"

  - name: "model_mixing"
    level_1: "single_model"
    level_2: "cheap_for_summaries"

# Utility weights favor cost (with quality floor)
utility_weights:
  quality: 0.3   # Minimum acceptable quality
  cost: 1.0      # Minimize cost
  time: 0.1
```

---

### Goal: Minimize Latency

**Experiment Design:**
```yaml
# Test latency-reduction variables
variables:
  - name: "context_loading"
    level_1: "static_upfront"
    level_2: "progressive_mcp"

  - name: "execution_mode"
    level_1: "sequential"
    level_2: "parallel"

  - name: "caching"
    level_1: "no_cache"
    level_2: "aggressive_cache"

  - name: "streaming"
    level_1: "batch"
    level_2: "streaming"

# Utility weights favor time (with quality floor)
utility_weights:
  quality: 0.3
  cost: 0.1
  time: 1.0
```

---

### Goal: Find Optimal Tradeoff

**Experiment Design:**
```yaml
# Test balanced configurations
variables:
  - name: "quality_tier"
    level_1: "good_enough"  # 75% quality target
    level_2: "high_quality" # 85% quality target

  - name: "cost_tier"
    level_1: "budget_conscious"
    level_2: "cost_no_object"

  - name: "speed_tier"
    level_1: "fast"         # <5s
    level_2: "thorough"     # >10s ok

  - name: "complexity"
    level_1: "simple"
    level_2: "sophisticated"

# Balanced utility weights
utility_weights:
  quality: 0.5
  cost: 0.3
  time: 0.2
```

---

## The Continuous Improvement Cycle

```
┌─────────────────────────────────────────┐
│         Sprint Planning                 │
│                                         │
│ Review usage data from last sprint:    │
│ - What did users complain about?       │
│ - Where is quality low?                │
│ - What costs too much?                 │
│ - What's too slow?                     │
└─────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────┐
│    Design Next L8 Experiment           │
│                                         │
│ Hypothesis: [Based on user feedback]  │
│ Variables: [4 testable variations]     │
│ Expected impact: [% improvement]       │
└─────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────┐
│    Run Experiment ($0.40, 10 min)      │
│                                         │
│ Main effects analysis                  │
│ Identify winning configuration         │
│ Understand variable contributions      │
└─────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────┐
│         Analyze Results                 │
│                                         │
│ - Does it fix the user complaint?      │
│ - What's the quality/cost/time impact? │
│ - Any unexpected interactions?         │
│ - What did we learn?                   │
└─────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────┐
│         Ship Improvement                │
│                                         │
│ Deploy winning configuration            │
│ Monitor metrics                         │
│ (Optional: A/B test first)             │
└─────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────┐
│      Gather User Feedback               │
│                                         │
│ 1-2 weeks of production usage          │
│ Collect: complaints, edge cases, ideas │
│ Measure: quality, cost, latency, NPS   │
└─────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────┐
│         Document Learnings              │
│                                         │
│ What worked? What didn't?              │
│ Update hypotheses for next iteration   │
│ Share with team                        │
└─────────────────────────────────────────┘
            ↓
    (Repeat next sprint)
```

---

## Anti-Patterns to Avoid

### ❌ Anti-Pattern 1: "Perfect Before Shipping"

**Mistake:**
```
Spend 3 months optimizing everything:
- Fine-tune prompts manually
- Add agentic workflows
- Build custom RAG system
- Fine-tune model
- THEN ship to users
```

**Why it fails:** Users might need something completely different

**Better approach:**
```
Sprint 1: Run L8, ship good enough (70% quality)
Sprint 2: Get user feedback, iterate
Sprint 3: Address biggest complaint
Sprint 4: Ship improvements
(Repeat based on real learnings)
```

---

### ❌ Anti-Pattern 2: "One-and-Done Optimization"

**Mistake:**
```
Run TesseractFlow once
Ship winning configuration
Never run experiments again
Assume optimal configuration never changes
```

**Why it fails:** Requirements evolve, users change, models improve

**Better approach:**
```
Run TesseractFlow every sprint
Each iteration addresses new learnings
Continuously improve based on reality
Re-validate assumptions periodically
```

---

### ❌ Anti-Pattern 3: "Optimize Everything Equally"

**Mistake:**
```
Spend equal time optimizing all 4 variables
Ignore main effects percentages
"Every variable deserves attention"
```

**Why it fails:** Wasted effort on low-impact variables (Pareto principle)

**Better approach:**
```
Follow main effects analysis:
- 52% contribution → Spend 3 sprints here
- 25% contribution → Spend 1 sprint here
- 15% contribution → Spend 1 sprint here
- 8% contribution → Skip it (not worth time)
```

---

### ❌ Anti-Pattern 4: "Ignore User Feedback"

**Mistake:**
```
Optimize for quality score only
Ignore user complaints about latency
"The lab results are great!"
Ship slow-but-accurate solution
Users complain and churn
```

**Why it fails:** Lab metrics ≠ real user satisfaction

**Better approach:**
```
Lab: Quality = 85%, Latency = 30s
Users: "It's too slow"
Next experiment: Optimize latency (even if quality drops to 80%)
Result: Users much happier with fast responses
```

---

### ❌ Anti-Pattern 5: "Over-Engineering"

**Mistake:**
```
"Let's add reflection loops!"
"Let's add multi-agent collaboration!"
"Let's add RLHF!"
"Let's fine-tune our own model!"
Complexity grows unbounded
```

**Why it fails:** Diminishing returns, maintenance burden

**Better approach:**
```
Each iteration: Add ONE thing
Measure: Does it improve quality/cost/latency?
If not: Remove it (simplicity is valuable)
Only add complexity when TesseractFlow proves it helps
```

---

## When to Stop Iterating

### Signal 1: Diminishing Returns

**Pattern:**
```
Sprint 1: 65% → 70% (+5%)
Sprint 2: 70% → 78% (+8%)
Sprint 3: 78% → 80% (+2%)
Sprint 4: 80% → 81% (+1%)  ← Diminishing returns
Sprint 5: 81% → 81.5% (+0.5%)  ← Stop here
```

**Decision:** You've hit the point of diminishing returns. Optimize something else or ship and iterate on a new feature.

---

### Signal 2: User Satisfaction High

**Pattern:**
```
NPS Score: 75 (excellent)
User complaints: <1% mention this feature
Quality: 80% (good enough)
Cost: Acceptable
Latency: Acceptable
```

**Decision:** Users are happy. Stop optimizing and work on something else.

---

### Signal 3: Cost of Optimization > Value of Improvement

**Pattern:**
```
Current: 82% quality, $0.02/request
Next experiment would test: Premium models for 85% quality, $0.10/request

Cost increase: 5x ($0.02 → $0.10)
Quality increase: 3.6% (82% → 85%)

ROI: Negative (paying 5x more for 3.6% improvement)
```

**Decision:** Not worth it. Stop optimizing quality, focus on cost reduction instead.

---

### Signal 4: Main Effects All Below 10%

**Pattern:**
```
Latest experiment results:
- Variable A: 8% contribution
- Variable B: 6% contribution
- Variable C: 5% contribution
- Variable D: 3% contribution

All variables have low impact!
```

**Decision:** You've optimized the high-impact variables. Remaining improvements are marginal. Stop iterating on this feature.

---

## Summary: The TesseractFlow Way

### Principles

1. **Ship fast, iterate often** - Get to production quickly, improve based on real usage
2. **Follow the data** - Main effects analysis tells you where to focus
3. **User feedback first** - Lab metrics are useful, but user satisfaction is what matters
4. **Embrace good enough** - 80% quality for $0.40 beats 95% quality for $1000
5. **Continuous improvement** - Run experiments every sprint, build on learnings
6. **Simplicity is valuable** - Only add complexity when data proves it helps

### Typical Journey

```
Sprint 1: Foundation (70% quality, $0.40)
Sprint 2: Optimize high-impact variable (78% quality, $0.40)
Sprint 3: Address user complaint (80% quality, 6x faster, $0.40)
Sprint 4: Prompt refinement (85% quality, $0.40)
Sprint 5: Cost optimization (82% quality, 35% cheaper, $0.40)

Total: $2.00, 5 sprints, 82% quality, 35% cost savings, 6x faster
```

### When to Use DSPy

**After 3-5 TesseractFlow iterations**, if:
- Architecture is stable (no more big changes)
- You need that last 10-15% quality improvement
- You have training data available
- You're ready to invest $5 and 3 hours in prompt perfection
- Users are happy but you want to optimize further

**Until then:** Keep iterating with TesseractFlow. $0.40 per sprint, fast learning, continuous improvement.

---

## Next Steps

1. **Read the examples** in `examples/code_review/` to see iteration patterns in action
2. **Run your first experiment** - Start with Pattern 1 (Start Broad, Then Narrow)
3. **Ship the winning config** - Get to production fast
4. **Gather user feedback** - Real usage data is gold
5. **Plan your next iteration** - Use Pattern 3 (User Feedback First)

**Remember:** TesseractFlow is not a one-shot optimizer. It's a continuous improvement engine. Run experiments every sprint, build on learnings, and continuously deliver value to users.
