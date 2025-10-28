# Feature Spec: Use Case Validation & Model Capability Mapping

**Feature ID:** 001.5-use-case-validation
**Version:** 0.1.5
**Status:** Planning
**Created:** 2025-10-26
**Priority:** Pre-v0.2 Release (Critical)

---

## Overview

Before releasing v0.2 (Web UI), validate TesseractFlow v0.1 CLI with 6+ diverse workflow use cases. Map DeepSeek R1 3.2 capabilities across task types, create reusable templates, and generate case studies for marketing.

**Strategic Value:**
- Prove framework works across domains (not just code review)
- Map budget model capabilities (DeepSeek R1 at $0.14/M tokens)
- Create production-ready workflow templates
- Generate blog-worthy case studies
- Test iteration patterns in practice

---

## Use Cases (6 Workflows)

### UC1: Code Review (Already Validated ✅)
**Status:** Complete (rubric.py experiment)
**Domain:** Software engineering
**Input:** Python file (100-500 lines)
**Output:** Code issues with severity, description, suggestions

**Quality Rubric (0-100):**
- Issue Detection (30 pts): Real bugs vs false positives
- Severity Accuracy (20 pts): Critical vs minor classification
- Actionability (20 pts): Clear fix suggestions
- Completeness (15 pts): Catches all major issues
- Code Understanding (15 pts): Demonstrates context awareness

**Reference:** `experiments/rubric_review_experiment.yaml`

---

### UC2: Fiction Scene Writing
**Status:** To be implemented
**Domain:** Creative writing (StoryPunk use case!)
**Input:** Scene outline + character sheets + world context
**Output:** 500-1000 word scene with dialogue and description

**Quality Rubric (0-100):**
- Character Consistency (25 pts): Voice, motivations, relationships accurate
- Plot Coherence (20 pts): Scene advances story, ties to outline
- Prose Quality (20 pts): Vivid descriptions, varied sentence structure
- Dialogue Authenticity (20 pts): Natural speech, distinct voices
- Emotional Impact (15 pts): Evokes intended emotions

**Test Dataset:** 5-10 scenes from StoryPunk backlog

**Variables to Test:**
- `context_strategy`: outline_only vs full_chapter vs progressive_discovery
- `generation_strategy`: standard vs chain_of_thought vs few_shot (2-3 example scenes)
- `model_tier`: deepseek vs haiku vs sonnet
- `temperature`: 0.7 vs 1.0 (creativity vs consistency)

---

### UC3: Business Documentation Generation
**Status:** To be implemented
**Domain:** Business/technical writing
**Input:** Meeting notes + product specs + stakeholder requirements
**Output:** 1-2 page PRD, technical spec, or stakeholder update

**Quality Rubric (0-100):**
- Completeness (25 pts): All required sections present
- Clarity (25 pts): Non-technical stakeholders can understand
- Accuracy (20 pts): Faithfully represents source material
- Structure (15 pts): Logical flow, proper formatting
- Actionability (15 pts): Clear next steps, owners, timelines

**Test Dataset:** Create 5-8 synthetic meeting notes scenarios
- Product feature spec
- Technical architecture doc
- Quarterly board update
- Customer onboarding guide
- Internal process documentation

**Variables to Test:**
- `context_strategy`: notes_only vs notes_plus_template vs notes_plus_examples
- `output_format`: markdown vs structured_json vs executive_summary
- `model_tier`: deepseek vs haiku
- `generation_strategy`: standard vs chain_of_thought

---

### UC4: Log Analysis & Incident Summarization
**Status:** To be implemented
**Domain:** DevOps/SRE
**Input:** 500-2000 lines of application logs + error traces
**Output:** Incident summary with root cause, impact, timeline

**Quality Rubric (0-100):**
- Root Cause Identification (30 pts): Correctly identifies primary failure
- Timeline Accuracy (20 pts): Reconstructs event sequence
- Impact Assessment (20 pts): Scope, affected users, data loss
- Technical Depth (15 pts): Stack traces, error codes explained
- Remediation Steps (15 pts): Immediate fixes + prevention

**Test Dataset:** Collect/generate 5-8 log scenarios
- Database connection failure
- Memory leak crash
- API rate limiting cascade
- Authentication service outage
- Data corruption incident

**Variables to Test:**
- `context_strategy`: logs_only vs logs_plus_metrics vs logs_plus_historical
- `summarization_style`: technical vs executive vs incident_report
- `model_tier`: deepseek vs haiku
- `analysis_depth`: quick_summary vs deep_analysis

---

### UC5: Knowledge Extraction from Documentation
**Status:** To be implemented
**Domain:** Information extraction
**Input:** 5-10 page technical doc (API docs, tutorials, whitepapers)
**Output:** Structured knowledge base entries (FAQ, concepts, examples)

**Quality Rubric (0-100):**
- Completeness (25 pts): Extracts all key concepts
- Accuracy (25 pts): No hallucinations, faithful to source
- Structure Quality (20 pts): Well-organized entries
- Usefulness (15 pts): Answers likely user questions
- Examples (15 pts): Includes code samples, edge cases

**Test Dataset:** Real documentation
- FastAPI official docs (5 pages)
- Streamlit tutorial (5 pages)
- LangGraph conceptual guide (5 pages)
- SQLAlchemy relationships (5 pages)
- Pydantic validation (5 pages)

**Variables to Test:**
- `extraction_strategy`: section_by_section vs full_doc vs query_based
- `output_format`: faq vs concept_map vs code_snippets
- `model_tier`: deepseek vs haiku
- `chunk_size`: 2000_tokens vs 8000_tokens

---

### UC6: Response Quality Rating (Meta-Evaluation)
**Status:** To be implemented
**Domain:** LLM evaluation (meta-task)
**Input:** User query + 3-5 LLM responses from different models
**Output:** Ranked responses with scores and justifications

**Quality Rubric (0-100):**
- Ranking Accuracy (30 pts): Matches human preferences
- Justification Quality (25 pts): Clear, specific reasoning
- Criteria Coverage (20 pts): Evaluates all relevant dimensions
- Consistency (15 pts): Similar queries get similar evaluations
- Calibration (10 pts): Scores align with ranking

**Test Dataset:** Create 10-15 evaluation scenarios
- Technical question (3 responses)
- Creative writing prompt (4 responses)
- Code generation task (3 responses)
- Data analysis question (4 responses)
- Ethical dilemma (3 responses)

**Variables to Test:**
- `rubric_detail`: simple vs comprehensive vs domain_specific
- `comparison_mode`: pairwise vs rank_all vs score_individually
- `model_tier`: deepseek vs haiku (can budget model evaluate itself?)
- `generation_strategy`: standard vs chain_of_thought

---

## Implementation Plan

### Phase 1: Infrastructure (Week 1, 8-12 hours)

**Create Workflow Implementations:**
- [ ] `workflows/fiction_scene.py` - Scene generation workflow
- [ ] `workflows/business_doc.py` - Documentation workflow
- [ ] `workflows/log_analysis.py` - Log analysis workflow
- [ ] `workflows/knowledge_extraction.py` - Knowledge extraction workflow
- [ ] `workflows/response_rating.py` - Response quality rating workflow

**Create Test Datasets:**
- [ ] `examples/fiction_scene/inputs/` - 5-10 scene outlines
- [ ] `examples/business_doc/inputs/` - 5-8 meeting notes
- [ ] `examples/log_analysis/inputs/` - 5-8 log files
- [ ] `examples/knowledge_extraction/inputs/` - 5 documentation pages
- [ ] `examples/response_rating/inputs/` - 10-15 response sets

**Create Quality Rubrics:**
- [ ] `examples/fiction_scene/rubric.yaml` - Creative writing rubric
- [ ] `examples/business_doc/rubric.yaml` - Documentation rubric
- [ ] `examples/log_analysis/rubric.yaml` - Incident analysis rubric
- [ ] `examples/knowledge_extraction/rubric.yaml` - Extraction rubric
- [ ] `examples/response_rating/rubric.yaml` - Meta-evaluation rubric

---

### Phase 2: Initial Experiments (Week 2, 12-16 hours)

**Run Baseline Experiments ($2-3 total cost):**
- [ ] Fiction Scene (L8, 8 tests × $0.05 = $0.40)
- [ ] Business Doc (L8, 8 tests × $0.05 = $0.40)
- [ ] Log Analysis (L8, 8 tests × $0.05 = $0.40)
- [ ] Knowledge Extraction (L8, 8 tests × $0.05 = $0.40)
- [ ] Response Rating (L8, 8 tests × $0.05 = $0.40)

**Document Findings:**
- [ ] Main effects for each workflow
- [ ] DeepSeek R1 strengths/weaknesses by domain
- [ ] Optimal configurations per use case
- [ ] Cross-workflow patterns

---

### Phase 3: Iteration Testing (Week 3, 12-16 hours)

**Test Iteration Patterns:**

Pick 2-3 workflows and run follow-up experiments based on findings:

**Example: Fiction Scene Iteration**
- Experiment 1: Architecture (context, model, strategy, temperature)
  - Finding: "Context matters most (52%), temperature second (28%)"
- Experiment 2: Deep dive on context
  - Test: outline_only vs full_chapter vs character_sheets vs world_bible
  - Finding: "Character sheets + world bible: +35% consistency"
- Experiment 3: Temperature tuning
  - Test: 0.5, 0.7, 0.9, 1.1 (narrow range)
  - Finding: "0.9 optimal (creativity + coherence)"

**Document Learnings:**
- [ ] Iteration ROI per workflow
- [ ] When to stop iterating (diminishing returns)
- [ ] Cross-workflow insights (do patterns generalize?)

---

### Phase 4: Case Study Creation (Week 4, 8-12 hours)

**Write Case Studies:**
- [ ] "Optimizing Fiction Scene Generation: 40% Quality Gain for $1.20"
- [ ] "Budget Models for Business Docs: DeepSeek vs Claude Haiku"
- [ ] "Log Analysis at Scale: Fast, Cheap Incident Summaries"

**Create Reusable Templates:**
- [ ] Package each workflow as ready-to-use template
- [ ] Include optimal configs from experiments
- [ ] Write usage guides

**Update Documentation:**
- [ ] Add workflows to README examples
- [ ] Create "Use Case Gallery" page
- [ ] Update quickstart with diverse examples

---

## Deliverables

### Code Artifacts
- 5 new workflow implementations (BaseWorkflowService subclasses)
- 30-50 test inputs across 5 domains
- 5 quality rubrics (YAML configs)
- 25-30 experiment configs

### Experiment Results
- 5-10 L8 experiments (~$2-5 total cost)
- Main effects analysis for each workflow
- Pareto frontiers (quality vs cost)
- DeepSeek R1 capability map

### Documentation
- 3-5 case study blog posts (1000-1500 words each)
- Workflow template gallery
- "Iteration Patterns in Practice" guide
- Updated README with diverse examples

### Knowledge Base
- 20-30 insights about DeepSeek R1
- Cross-workflow optimization patterns
- Domain-specific best practices

---

## Success Metrics

### Technical Validation
- [ ] All 5 workflows run successfully
- [ ] Quality rubrics produce meaningful scores (0-100 range)
- [ ] Main effects analysis identifies clear winners
- [ ] Iteration patterns demonstrate ROI

### Model Capability Mapping
- [ ] DeepSeek R1 performance across 5 domains documented
- [ ] Strengths/weaknesses identified
- [ ] Cost/quality trade-offs quantified
- [ ] Comparison to Haiku/Sonnet (where applicable)

### Marketing Value
- [ ] 3+ blog-worthy case studies
- [ ] Diverse examples for website/docs
- [ ] Proof of framework generalization
- [ ] StoryPunk validation complete

---

## Timeline

**Week 1:** Infrastructure (workflows, datasets, rubrics)
**Week 2:** Initial experiments (5 workflows × L8)
**Week 3:** Iteration testing (2-3 workflows × 2-3 iterations)
**Week 4:** Case studies + templates + docs

**Total:** 40-56 hours over 4 weeks
**Cost:** $2-5 in LLM API calls
**Target Completion:** Before v0.2 implementation starts

---

## Risk Mitigation

### Risk 1: Creating Quality Rubrics is Hard
**Mitigation:** Start with code review rubric as template. For StoryPunk, leverage existing quality criteria. Research domain standards for others.

### Risk 2: Test Data Creation is Time-Consuming
**Mitigation:** Use real data where possible (StoryPunk scenes, public docs). Synthetic data for privacy-sensitive domains (logs, business docs).

### Risk 3: Budget Model (DeepSeek) May Underperform
**Mitigation:** That's the point! Document where it fails. Use Haiku as baseline. Sonnet for comparison.

### Risk 4: Results May Not Be Blog-Worthy
**Mitigation:** Focus on learnings, not just wins. "When Budget Models Fail" is also valuable content. Emphasize iteration patterns.

---

## Integration with v0.2

**Knowledge Base Seeding:**
All insights from these experiments will seed the v0.2 knowledge base:
- Model capabilities (DeepSeek R1 strengths/weaknesses)
- Workflow patterns (what works across domains)
- Optimization strategies (context > temperature for creative tasks)

**Template Gallery:**
v0.2 Web UI will feature these workflows as starting templates:
- "Start from Template" dropdown
- Pre-filled optimal configs
- Domain-specific rubrics

**Marketing Content:**
Case studies will drive v0.2 launch:
- Blog posts on launch day
- Tweet threads with findings
- Reddit posts with experiment data

---

## References

- Iteration Patterns: `docs/iteration-patterns.md`
- Code Review Experiment: `experiments/rubric_review_experiment.yaml`
- StoryPunk Use Case: `docs/CONVERSATION_SUMMARY_2025_10_26.md`
- v0.2 Planning: `specs/002-web-ui-api/`
