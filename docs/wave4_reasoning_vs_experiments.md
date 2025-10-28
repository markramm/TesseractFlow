# Wave 4: Reasoning & Verbalized Sampling Experiments

**Research Question:** Do reasoning and verbalized sampling techniques improve non-reasoning creative workflows?

**Created:** 2025-10-28
**Status:** Experiment designs complete, ready for execution
**Estimated Cost:** ~$0.30-0.40 for n=5 replications (all 4 experiments)
**Estimated Time:** ~30-40 minutes total

## Overview

Wave 4 experiments test the newly implemented `ReasoningMixin` and `VerbalizationMixin` on four fiction writing workflows to determine if these techniques improve quality for creative tasks that don't inherently require reasoning.

## Research Motivation

The mixin implementation (tesseract_flow/core/mixins.py:1-461) provides two key capabilities:

### ReasoningMixin
- Automatically detects model type (DeepSeek R1/V3.2) and applies correct reasoning parameters
- Falls back to Chain-of-Thought prompting for other models
- Controls reasoning visibility (visible/hidden traces)

### VerbalizationMixin
- **Self-consistency:** Generate N samples, return most common answer
- **Sample-and-rank:** Generate N samples, use evaluator to rank them
- **Ensemble:** Generate with different approaches (analytical, creative, methodical), synthesize results

**Key Question:** Do these techniques, proven effective for reasoning tasks, also improve creative fiction generation?

## Variable Selection Strategy

For each experiment, we:
1. **KEPT** high-impact variables (temperature, domain-specific variables)
2. **DROPPED** low-impact variables (examples_count, prose_style, output_format)
3. **ADDED** 5 new variables to test reasoning and verbalized sampling

This maintains the Taguchi L8 constraint (7 variables, 2 levels, 8 experiments) while maximizing learning.

## Experiment Designs

### 1. Fiction Scene Generation with Reasoning & VS
**File:** `experiments/wave4_fiction_reasoning_vs.yaml`
**Workflow:** `fiction_scene`

**Variables (7):**
1. `temperature` (0.5/0.9) - HIGH IMPACT KEPT
2. `context_depth` (minimal/full) - HIGH IMPACT KEPT
3. `reasoning_enabled` (false/true) - NEW
4. `verbalized_sampling` (none/self_consistency) - NEW
5. `n_samples` (3/5) - NEW
6. `reasoning_visibility` (visible/hidden) - NEW
7. `max_reasoning_tokens` (standard/extended) - NEW

**Dropped Variables:**
- `generation_strategy` (standard/CoT) - Replaced by reasoning_enabled
- `prose_style` (concise/lyrical) - LOW IMPACT

**Expected Learnings:**
- Does reasoning help with narrative structure and story logic?
- Does self-consistency produce better creative output by averaging multiple samples?
- Is there a cost/quality tradeoff worth making?
- Do hidden reasoning traces maintain creativity while reducing output tokens?
- Is extended reasoning budget worthwhile for complex scenes?

---

### 2. Dialogue Enhancement with Reasoning & VS
**File:** `experiments/wave4_dialogue_reasoning_vs.yaml`
**Workflow:** `dialogue_enhancement`

**Variables (7):**
1. `temperature` (0.6/0.9) - HIGH IMPACT KEPT
2. `voice_emphasis` (subtle/explicit) - HIGH IMPACT KEPT
3. `reasoning_enabled` (false/true) - NEW
4. `verbalized_sampling` (none/sample_and_rank) - NEW
5. `n_samples` (3/5) - NEW
6. `ranking_criteria` (naturalness_and_voice/emotional_authenticity) - NEW
7. `reasoning_visibility` (visible/hidden) - NEW

**Dropped Variables:**
- `generation_strategy` (standard/CoT) - Replaced by reasoning_enabled
- `examples_count` (0/3) - LOW IMPACT

**Expected Learnings:**
- Does reasoning help maintain character voice consistency across dialogue?
- Does sample-and-rank select more natural-sounding dialogue?
- Which ranking criteria (naturalness vs emotional authenticity) works better?
- Is the cost of generating 3-5 samples worth the quality improvement?
- Does reasoning visibility affect dialogue quality?

---

### 3. Character Development with Reasoning & VS
**File:** `experiments/wave4_character_reasoning_vs.yaml`
**Workflow:** `character_development`

**Variables (7):**
1. `temperature` (0.4/0.7) - HIGH IMPACT KEPT
2. `revision_strategy` (refine/regenerate) - HIGH IMPACT KEPT
3. `reasoning_enabled` (false/true) - NEW
4. `verbalized_sampling` (none/ensemble) - NEW
5. `ensemble_approaches` (analytical_creative/analytical_creative_methodical) - NEW
6. `n_samples` (2/3) - NEW
7. `reasoning_visibility` (visible/hidden) - NEW

**Dropped Variables:**
- `generation_strategy` (standard/CoT) - Replaced by reasoning_enabled
- `output_format` (freeform/structured_json) - LOW IMPACT

**Expected Learnings:**
- Does reasoning help maintain character trait consistency across updates?
- Does ensemble generation (analytical + creative + methodical) produce richer character development?
- Is the cost of 2-3 ensemble samples worth the quality improvement?
- Does reasoning visibility affect character update quality?
- Which ensemble approach (2 or 3 perspectives) works better?

---

### 4. Progressive Discovery with Reasoning & VS
**File:** `experiments/wave4_discovery_reasoning_vs.yaml`
**Workflow:** `progressive_discovery`

**Variables (7):**
1. `temperature` (0.5/0.8) - HIGH IMPACT KEPT
2. `revelation_depth` (surface/deep) - HIGH IMPACT KEPT
3. `reasoning_enabled` (false/true) - NEW
4. `verbalized_sampling` (none/self_consistency) - NEW
5. `n_samples` (3/5) - NEW
6. `verification_step` (none/verify_consistency) - NEW
7. `reasoning_visibility` (visible/hidden) - NEW

**Dropped Variables:**
- `generation_strategy` (standard/CoT) - Replaced by reasoning_enabled
- `reveal_frequency` (sparse/frequent) - LOWER IMPACT than depth

**Expected Learnings:**
- Does reasoning help maintain world-building consistency across revelations?
- Does self-consistency produce more impactful discoveries by selecting common elements?
- Is the verification step worthwhile for catching logical inconsistencies?
- Does reasoning visibility affect revelation quality?
- Do 3 or 5 samples work better for progressive discovery?

## Utility Weights

All experiments prioritize quality, reflecting the goal of improving creative output:

- **Fiction Scene:** Quality 0.8, Cost 0.15, Time 0.05
- **Dialogue:** Quality 0.7, Cost 0.2, Time 0.1
- **Character:** Quality 0.75, Cost 0.15, Time 0.1
- **Discovery:** Quality 0.8, Cost 0.15, Time 0.05

## Rubric Adaptations

Each rubric has been updated to specifically evaluate whether reasoning and verbalized sampling improve the relevant quality dimensions:

### Fiction Scene
- **Creativity:** Does reasoning help generate more creative content?
- **Consistency:** Does reasoning maintain better consistency?
- **Prose Quality:** Do multiple samples improve prose?
- **Dialogue:** Does self-consistency improve dialogue?

### Dialogue Enhancement
- **Voice Distinctiveness:** Does reasoning help maintain character voice?
- **Natural Flow:** Does sample-and-rank select better flow?
- **Emotional Authenticity:** Do multiple samples improve authenticity?

### Character Development
- **Continuity Preservation:** Does reasoning track traits better?
- **Arc Progression:** Does ensemble combine perspectives better?
- **Utility for Writers:** Does verbalized sampling add value?

### Progressive Discovery
- **World Consistency:** Does reasoning help maintain consistency?
- **Revelation Impact:** Does self-consistency improve impact?
- **Integration Quality:** Does verification help?

## Expected Cost Analysis

**Per Experiment (n=5 replications):**
- 8 tests × 5 replications = 40 total tests
- ~2,000-3,000 tokens per generation (fiction)
- ~500-1,000 tokens per evaluation
- With verbalized sampling (3-5 samples): 3-5× generation cost
- **Estimated:** ~$0.08-0.12 per experiment at n=5

**All 4 Experiments (n=5):**
- **Total Cost:** ~$0.32-0.48
- **Total Time:** ~30-45 minutes
- **Total Tests:** 160 (40 per experiment)

## Comparison with Baseline (Wave 1)

Wave 4 experiments will directly compare against Wave 1 baselines:
- `deepseek_fiction_scene_generation.yaml` (Wave 1) → `wave4_fiction_reasoning_vs.yaml` (Wave 4)
- `deepseek_dialogue_enhancement.yaml` (Wave 1) → `wave4_dialogue_reasoning_vs.yaml` (Wave 4)
- `deepseek_character_development.yaml` (Wave 1) → `wave4_character_reasoning_vs.yaml` (Wave 4)
- `deepseek_progressive_discovery.yaml` (Wave 1) → `wave4_discovery_reasoning_vs.yaml` (Wave 4)

## Running the Experiments

### Quick Validation (n=1, ~5-8 minutes, ~$0.04-0.06)
```bash
# Test all 4 experiments at n=1 for quick validation
source .env && export OPENROUTER_API_KEY
.venv/bin/tesseract experiment run experiments/wave4_fiction_reasoning_vs.yaml --output experiments/wave4_fiction_n1.json --use-cache --record-cache
.venv/bin/tesseract experiment run experiments/wave4_dialogue_reasoning_vs.yaml --output experiments/wave4_dialogue_n1.json --use-cache --record-cache
.venv/bin/tesseract experiment run experiments/wave4_character_reasoning_vs.yaml --output experiments/wave4_character_n1.json --use-cache --record-cache
.venv/bin/tesseract experiment run experiments/wave4_discovery_reasoning_vs.yaml --output experiments/wave4_discovery_n1.json --use-cache --record-cache
```

### Full Experiment Run (n=5, ~30-45 minutes, ~$0.32-0.48)
```bash
# Run all 4 experiments with n=5 replications for statistical validity
source .env && export OPENROUTER_API_KEY

echo "1/4: Fiction Scene with Reasoning & VS..."
.venv/bin/tesseract experiment run experiments/wave4_fiction_reasoning_vs.yaml --output experiments/wave4_fiction_n5.json --replications 5 --use-cache --record-cache

echo "2/4: Dialogue Enhancement with Reasoning & VS..."
.venv/bin/tesseract experiment run experiments/wave4_dialogue_reasoning_vs.yaml --output experiments/wave4_dialogue_n5.json --replications 5 --use-cache --record-cache

echo "3/4: Character Development with Reasoning & VS..."
.venv/bin/tesseract experiment run experiments/wave4_character_reasoning_vs.yaml --output experiments/wave4_character_n5.json --replications 5 --use-cache --record-cache

echo "4/4: Progressive Discovery with Reasoning & VS..."
.venv/bin/tesseract experiment run experiments/wave4_discovery_reasoning_vs.yaml --output experiments/wave4_discovery_n5.json --replications 5 --use-cache --record-cache
```

## Analysis Plan

After running experiments, analyze:

1. **Main Effects Analysis:**
   - Which variables have the highest impact on quality?
   - Is `reasoning_enabled` a significant factor?
   - Does `verbalized_sampling` improve quality?
   - What's the cost/quality tradeoff?

2. **Comparison with Baselines:**
   - Do Wave 4 configs outperform Wave 1 baselines?
   - Is the added cost of reasoning/verbalized sampling justified?

3. **Pareto Frontier:**
   - What's the best quality/cost/time tradeoff?
   - Does verbalized sampling shift the Pareto frontier?

4. **Variable Interactions:**
   - Does reasoning visibility affect quality?
   - Do certain verbalized sampling techniques work better with reasoning?
   - Is there an optimal n_samples value?

## Success Criteria

Wave 4 experiments are successful if:

1. ✅ **Quality Improvement:** At least one configuration shows statistically significant quality improvement over Wave 1 baseline
2. ✅ **Cost Justification:** Quality improvements justify the added cost of multiple samples
3. ✅ **Actionable Insights:** Main effects analysis clearly identifies which techniques work best
4. ✅ **Implementation Validation:** Mixins work correctly and integrate seamlessly with workflows

## Next Steps

After Wave 4 completion:

1. **Analyze Results:** Run main effects analysis and Pareto frontier visualization
2. **Document Findings:** Create summary of which techniques work best for creative workflows
3. **Optimize Workflows:** Update fiction writing workflows to use best-performing techniques
4. **Consider v0.3:** If successful, plan for expanding to other workflow types (lore expansion, thinking styles)

## References

- **Mixin Implementation:** tesseract_flow/core/mixins.py:1-461
- **Mixin Tests:** tests/unit/test_mixins.py:1-236
- **Wave 1 Baselines:** experiments/deepseek_fiction_scene_generation.yaml (and 3 others)
- **Project Documentation:** CLAUDE.md (v0.1.1 Released, v0.2 Planning)
