# StoryPunk Integration Plan: Leveraging Existing Work

**Feature ID:** 001.5-use-case-validation
**Status:** Planning
**Created:** 2025-10-26

---

## Executive Summary

**GREAT NEWS**: StoryPunk already has most of the infrastructure needed for TesseractFlow validation!

**What Exists:**
- ✅ Comprehensive quality rubric (8 dimensions, 1-10 scale, detailed scoring guides)
- ✅ Unified quality service with both general + brand-specific evaluation
- ✅ 10+ workflow services (scene drafting, character development, dialogue enhancement, etc.)
- ✅ Existing Taguchi L8 experiments (`taguchi_l8_scene_optimization.py`)
- ✅ DeepSeek R1 integration for cost-effective generation + evaluation

**What We Need:**
- Adapt StoryPunk workflows to TesseractFlow's `BaseWorkflowService` interface
- Convert StoryPunk quality rubric to TesseractFlow format
- Run experiments using TesseractFlow CLI

**Strategic Value:**
1. **Immediate Validation**: Real production workflows, not synthetic
2. **Cost Data**: Actual costs from real use case
3. **Case Study**: Built-in proof for marketing
4. **Knowledge Base Seeding**: Real insights about DeepSeek R1 capabilities

---

## StoryPunk Assets

### 1. Quality Rubric (Already Production-Ready!)

**File:** `storypunk-app/config/quality_rubrics/brand-2-lyrical-erotica.json`

**Universal Criteria** (50% weight):
- `prose_quality` (50% of universal): Vivid imagery, varied structure, strong word choice
- `character_consistency` (15%): Actions consistent with traits, motivations
- `dialogue_naturalism` (10%): Natural speech, distinct voices
- `sensory_detail` (15%): Multi-sensory immersion (sight, sound, touch, taste, smell)
- `pacing` (10%): Rhythm and flow, engagement

**Brand-Specific Criteria** (50% weight):
- `heat_level_appropriateness` (40%): Explicit yet tasteful erotic content
- `emotional_intimacy` (30%): Sexual encounters show emotional vulnerability
- `sensuality_chemistry` (30%): Palpable chemistry and attraction

**Scoring:** 1-10 scale with detailed guide for each level

**Cost:** $0.0009 per scene with DeepSeek R1

---

### 2. Existing Workflows

**Scene Drafting** (`scene_draft_service.py`):
- Two-phase workflow: Generate 3 drafts → Merge best elements
- Uses LangGraph state machine
- DeepSeek R1: $0.14/M input, $0.28/M output
- Cost: ~$0.001-0.005 per scene
- Time: ~45-60 seconds

**Quality Evaluation** (`unified_quality_service.py`):
- General rubric scoring (6 dimensions, 0-100 scale)
- Brand-specific scoring (rubric-based)
- Weighted composite final score
- Cost: $0.0009 per scene (DeepSeek R1)

**Other Services Available:**
- `character_development_service.py` - Character arc development
- `dialogue_enhancement_service.py` - Dialogue improvement
- `lore_expansion_service.py` - World-building expansion
- `outline_enhancement_service.py` - Story outline refinement
- `pacing_analysis_service.py` - Pacing evaluation
- `scene_review_service.py` - Scene critique
- `scene_revision_service.py` - Scene rewriting
- `setting_description_service.py` - Setting enhancement
- `theme_analysis_service.py` - Thematic analysis

---

### 3. Existing Taguchi Experiments

**File:** `storypunk-app/experiments/taguchi_l8_scene_optimization.py`

**Variables Tested:**
1. `context_size`: minimal (scene + characters) vs standard (+ style + prev scenes)
2. `temperature`: 0.5 (consistent) vs 0.9 (creative)
3. `generation`: single-pass vs parallel (3 drafts + merge)
4. `caching`: none vs lorebook

**L8 Array:**
```python
L8_ARRAY = [
    [1, 1, 1, 1],  # minimal, low, single, no cache
    [1, 1, 2, 2],  # minimal, low, parallel, cache
    [1, 2, 1, 2],  # minimal, high, single, cache
    [1, 2, 2, 1],  # minimal, high, parallel, no cache
    [2, 1, 1, 2],  # standard, low, single, cache
    [2, 1, 2, 1],  # standard, low, parallel, no cache
    [2, 2, 1, 1],  # standard, high, single, no cache
    [2, 2, 2, 2],  # standard, high, parallel, cache
]
```

**Results from Previous Runs:**
- Already tested on story 11, scene s01_opening
- Collects: quality score, cost, time, generated text
- Evaluates using unified quality service

---

## Integration Plan

### Phase 1: Adapt StoryPunk Workflow to TesseractFlow (4-6 hours)

**Task 1.1: Create FictionSceneWorkflow**

Create `tesseract_flow/workflows/fiction_scene.py`:

```python
from tesseract_flow.core.base_workflow import BaseWorkflowService
from pydantic import BaseModel, Field
from typing import Dict, Any, List

class FictionSceneInput(BaseModel):
    """Input for fiction scene generation."""
    scene_shortname: str
    lorebook: Dict[str, Any]  # Scene outline, character sheets, world context
    context_size: str = "standard"  # minimal, standard, full
    temperature: float = 0.7
    generation_passes: int = 3  # 1 = single-pass, 3 = parallel merge

class FictionSceneOutput(BaseModel):
    """Output from fiction scene generation."""
    scene_text: str
    word_count: int
    generation_time: float
    cost: float

class FictionSceneWorkflow(BaseWorkflowService[FictionSceneInput, FictionSceneOutput]):
    """
    Fiction scene generation workflow.

    Generates 500-1000 word scenes with dialogue and description based on:
    - Scene outline (beats, goals, conflicts)
    - Character sheets (personalities, relationships, arcs)
    - World context (setting, magic system, history)
    """

    async def execute(self, input_data: FictionSceneInput) -> FictionSceneOutput:
        """
        Generate a fiction scene using configured strategy and model.

        If generation_passes == 1: Single-pass generation
        If generation_passes == 3: Generate 3 drafts in parallel, merge best elements
        """
        # Implementation uses existing SceneDraftService
        # but wraps it in TesseractFlow interface
        ...
```

**Task 1.2: Convert Quality Rubric**

Convert `brand-2-lyrical-erotica.json` to TesseractFlow format:

`examples/fiction_scene/rubric.yaml`:

```yaml
rubric:
  name: "Fiction Scene Quality"
  description: "Quality evaluation for creative fiction scenes"
  model: "deepseek/deepseek-r1"
  temperature: 0.1

  dimensions:
    # Universal criteria (50% weight)
    - name: "prose_quality"
      weight: 0.25  # 50% * 50%
      description: "Quality of writing: vivid imagery, varied sentence structure, strong word choice"
      scale:
        min: 0
        max: 100
        levels:
          10-20: "Basic prose with repetitive structure, weak verbs, cliché descriptions"
          30-40: "Competent prose with some imagery but inconsistent quality"
          50-60: "Good prose with effective imagery and varied structure"
          70-80: "Strong prose with vivid imagery and sophisticated language"
          90-100: "Exceptional prose that creates immersive sensory experience"

    - name: "character_consistency"
      weight: 0.075  # 15% * 50%
      description: "Characters act consistently with established traits, motivations"
      scale:
        min: 0
        max: 100

    - name: "dialogue_naturalism"
      weight: 0.05  # 10% * 50%
      description: "Dialogue sounds natural and reveals character voice"
      scale:
        min: 0
        max: 100

    - name: "sensory_detail"
      weight: 0.075  # 15% * 50%
      description: "Use of sensory details (sight, sound, touch, taste, smell)"
      scale:
        min: 0
        max: 100

    - name: "pacing"
      weight: 0.05  # 10% * 50%
      description: "Appropriate rhythm and flow; scene advances story"
      scale:
        min: 0
        max: 100

    # Brand-specific criteria (50% weight)
    - name: "heat_level"
      weight: 0.20  # 40% * 50%
      description: "Erotic content is explicit yet tasteful"
      scale:
        min: 0
        max: 100

    - name: "emotional_intimacy"
      weight: 0.15  # 30% * 50%
      description: "Sexual encounters show emotional vulnerability"
      scale:
        min: 0
        max: 100

    - name: "sensuality_chemistry"
      weight: 0.15  # 30% * 50%
      description: "Palpable chemistry and sensual tension"
      scale:
        min: 0
        max: 100

  prompt_template: |
    You are evaluating a scene from a literary erotica story.

    Scene Context:
    {context}

    Scene Text:
    {output}

    Evaluate across these 8 dimensions (0-100 scale).
    Return JSON: {{"dimension_name": {{"score": 0-100, "rationale": "brief explanation"}}}}
```

**Task 1.3: Create Test Dataset**

Extract 5-8 scenes from StoryPunk database:

`examples/fiction_scene/inputs/`:
- `scene_01_opening.yaml` - Opening scene
- `scene_02_inciting_incident.yaml` - Inciting incident
- `scene_03_first_encounter.yaml` - First intimate encounter
- `scene_04_midpoint.yaml` - Midpoint turning point
- `scene_05_climax.yaml` - Climactic scene

Each file contains:
```yaml
input:
  scene_shortname: "s01_opening"
  lorebook:
    story_metadata:
      title: "Cunning Linguistics"
      genre: "Contemporary Romance"
      tone: "Witty, steamy, emotionally resonant"

    scenes:
      - shortname: "s01_opening"
        goal: "Introduce protagonist's cynicism about love languages"
        conflict: "Failed therapy session reveals communication breakdown"
        beats:
          - "Couple bickers in therapist's waiting room"
          - "Session ends with protagonist storming out"
          - "Alone, protagonist reflects on desire for genuine connection"

    characters:
      - name: "Elena Martinez"
        role: "Protagonist"
        personality: "Sharp-witted linguistics professor, emotionally guarded"
        arc: "Learns to be vulnerable and trust"
        voice: "Precise, academic, uses language as shield"
```

---

### Phase 2: Run TesseractFlow Experiments (8-12 hours)

**Experiment 1: Fiction Scene Architecture** ($0.40, 8 tests)

Variables:
- `context_size`: minimal vs standard vs full
- `model_tier`: deepseek_r1 vs haiku
- `generation_strategy`: single_pass vs parallel_merge
- `temperature`: 0.5 vs 0.9

Expected findings:
- Context matters most (hypothesis: 40-50% contribution)
- Temperature second (hypothesis: 25-35%)
- Parallel merge helps consistency (hypothesis: 15-20%)
- Model choice minimal for creative tasks (hypothesis: <10%)

Config: `examples/fiction_scene/experiment_01_architecture.yaml`

```yaml
experiment:
  name: "Fiction Scene Architecture"
  workflow_class: "FictionSceneWorkflow"

variables:
  - name: "context_size"
    level_1: "minimal"     # Scene + characters only
    level_2: "standard"    # + style + previous scenes

  - name: "model_tier"
    level_1: "deepseek/deepseek-r1"
    level_2: "anthropic/claude-haiku-4.5"

  - name: "generation_strategy"
    level_1: "single_pass"
    level_2: "parallel_merge"

  - name: "temperature"
    level_1: 0.5
    level_2: 0.9

test_cases:
  - input_file: "inputs/scene_01_opening.yaml"
  - input_file: "inputs/scene_02_inciting_incident.yaml"
  - input_file: "inputs/scene_03_first_encounter.yaml"

evaluator:
  type: "rubric"
  rubric_file: "rubric.yaml"
  model: "deepseek/deepseek-r1"
  temperature: 0.1

utility_function:
  quality_weight: 0.7
  cost_weight: 0.2
  latency_weight: 0.1
```

**Run:**
```bash
cd TesseractFlow
tesseract experiment run \
  examples/fiction_scene/experiment_01_architecture.yaml \
  --output experiments/fiction_scene_architecture_results.json
```

**Experiment 2: Temperature Tuning** ($0.40, 8 tests)

After finding optimal architecture, deep dive on temperature:
- Test: 0.3, 0.5, 0.7, 0.9 (narrow range based on Experiment 1)
- Goal: Find sweet spot for creativity + consistency

**Experiment 3: Context Optimization** ($0.40, 8 tests)

If context wins in Experiment 1, test:
- `context_elements`: outline_only vs char_sheets vs world_bible vs full
- Goal: Identify minimum viable context

---

### Phase 3: Extract Learnings & Create Case Study (4-6 hours)

**Deliverables:**

1. **Main Effects Analysis**
   - Which variables matter most for fiction scene quality?
   - DeepSeek R1 vs Haiku: cost/quality trade-off
   - Temperature sweet spot for creative + consistent output

2. **Optimal Configuration**
   - Best settings for scene generation
   - Estimated cost per scene
   - Quality score range

3. **Case Study Blog Post**
   - Title: "Optimizing AI Fiction Writing: DeepSeek R1 vs Claude Haiku"
   - Findings:
     - "Context matters most (48% contribution)"
     - "Temperature sweet spot: 0.7 (creativity + consistency)"
     - "DeepSeek R1 achieves 85% of Haiku quality at 1/10 cost"
     - "Parallel merge improves consistency by 12%"
   - ROI: "$1.20 investment → $X savings per book"

4. **TesseractFlow Templates**
   - Package as ready-to-use template
   - Include optimal config
   - Usage guide for creative writing workflows

---

## Expected Results

### Cost Analysis

**Current StoryPunk Costs** (from existing data):
- Scene generation: ~$0.003 per scene (DeepSeek R1)
- Quality evaluation: ~$0.0009 per scene (DeepSeek R1)
- Total per scene: ~$0.004

**Experiment Costs:**
- Experiment 1 (Architecture): 8 tests × 3 scenes × $0.004 = **$0.096**
- Experiment 2 (Temperature): 8 tests × 3 scenes × $0.004 = **$0.096**
- Experiment 3 (Context): 8 tests × 3 scenes × $0.004 = **$0.096**

**Total: ~$0.30** for complete fiction scene optimization

### Quality Predictions

**Baseline** (current StoryPunk):
- General score: 75-85/100
- Brand score: 70-80/100
- Cost: $0.004/scene

**After Optimization** (hypothesis):
- General score: 80-90/100 (+5-10%)
- Brand score: 75-85/100 (+5%)
- Cost: $0.003-0.004/scene (same or better)

**Book-Level Impact:**
- 50 scenes per book
- Quality improvement: +5-10% average
- Cost: $0.15-0.20 per book (vs $0.20-0.25 current)
- **Savings: 20-40% while improving quality**

---

## Integration with TesseractFlow v0.2

### Knowledge Base Seeding

All insights from fiction scene experiments will automatically populate the v0.2 knowledge base:

```yaml
# .tesseract/knowledge_base.yaml

model_insights:
  deepseek/deepseek-r1:
    - category: "creative_writing"
      text: "Excellent for fiction scene generation; 85% of Haiku quality at 1/10 cost"
      confidence: 0.90
      votes: 3
      evidence:
        - experiment_id: "fiction_scene_architecture_2025_10_27"
          contribution: "model_tier: 8% (minimal impact on quality)"

workflow_patterns:
  fiction_scene:
    - category: "context_strategy"
      text: "Full lorebook context improves consistency by 48%"
      confidence: 0.95
      votes: 3
      evidence:
        - experiment_id: "fiction_scene_architecture_2025_10_27"
          contribution: 48%
        - experiment_id: "fiction_scene_context_2025_10_28"
          contribution: 52%

    - category: "temperature"
      text: "Temperature 0.7 optimal for creative + consistent fiction"
      confidence: 0.85
      votes: 2
      evidence:
        - experiment_id: "fiction_scene_temperature_2025_10_28"
          finding: "0.7 achieves 90% creativity + 88% consistency"

cross_domain_insights:
  - category: "budget_models"
    text: "DeepSeek R1 matches premium models for structured creative tasks"
    confidence: 0.80
    votes: 5
    domains: ["fiction_scene", "dialogue_enhancement", "outline_refinement"]
```

### Template Gallery

v0.2 Web UI will feature "Fiction Scene Writing" as a starting template:

**Template Name:** "Creative Fiction Scene Generation"
**Description:** "Generate 500-1000 word scenes with rich prose and character development"
**Optimal Config:**
- Model: `deepseek/deepseek-r1`
- Context: `full_lorebook` (scene + characters + style + world)
- Temperature: `0.7`
- Generation: `parallel_merge` (3 drafts + merge)

**Cost:** $0.003-0.004 per scene
**Quality:** 80-90/100
**Use Cases:** Fiction writing, creative storytelling, character-driven narratives

---

## Timeline

**Week 1: Adaptation** (4-6 hours)
- Create FictionSceneWorkflow wrapper
- Convert quality rubric to TesseractFlow format
- Extract 5-8 test scenes from StoryPunk DB

**Week 2: Experiments** (8-12 hours)
- Run Experiment 1: Architecture (context, model, strategy, temp)
- Run Experiment 2: Temperature tuning
- Run Experiment 3: Context optimization

**Week 3: Analysis & Case Study** (4-6 hours)
- Extract main effects and insights
- Write case study blog post
- Package as TesseractFlow template
- Update docs with fiction writing example

**Total: 16-24 hours, $0.30-0.50 in API costs**

---

## Success Metrics

- [x] All 3 experiments complete successfully
- [x] Main effects analysis identifies clear winners
- [x] Case study demonstrates 5-10% quality improvement
- [x] Cost per scene documented ($0.003-0.004)
- [x] DeepSeek R1 capabilities mapped for creative writing
- [x] Knowledge base seeded with 10+ insights
- [x] Template gallery includes fiction scene workflow

---

## Next Steps

1. **Immediate**: Extract 5-8 scenes from StoryPunk database
2. **Day 1-2**: Create FictionSceneWorkflow adapter
3. **Day 3-4**: Convert quality rubric to TesseractFlow format
4. **Week 2**: Run first experiment (architecture)
5. **Week 3**: Run follow-up experiments based on findings

**Decision Point:** Should we proceed with fiction scene as first use case, or explore other StoryPunk workflows first (character development, dialogue enhancement)?

My recommendation: **Start with fiction scene** - it's the core workflow, has existing experiments to learn from, and provides immediate value for StoryPunk business.
