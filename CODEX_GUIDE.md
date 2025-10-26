# TesseractFlow Implementation Guide for ChatGPT Codex

**Branch:** `001-mvp-optimizer`
**Status:** Specifications Complete, Ready for Implementation
**Estimated Effort:** 135 tasks, 65-75 hours

---

## Getting Started

### 1. Read the Specifications (in order)

```bash
specs/001-mvp-optimizer/
├── spec.md          # START HERE - User stories, requirements, success criteria
├── plan.md          # Technical architecture, dependencies, constraints
├── research.md      # 5 key technical decisions (Taguchi, CLI, etc.)
├── data-model.md    # 10 entities with relationships
├── quickstart.md    # Complete user walkthrough example
├── tasks.md         # 132 tasks with dependencies - YOUR ROADMAP
└── contracts/
    ├── cli-commands.md   # CLI command specifications
    └── core-apis.md      # Internal API contracts
```

### 2. Understand the Constitution

Read `.specify/memory/constitution.md` for 6 core principles that govern all decisions:
1. Workflows-as-Boundaries (HITL pattern)
2. Generation Strategies as Variables
3. Multi-Objective Optimization
4. Provider Agnostic
5. Transparency Over Automation
6. Test-Driven Core (≥80% coverage)

### 3. Follow the Task Breakdown

Implement in order from `tasks.md`:
- **Phase 1:** Setup (T001-T007) - 2-4 hours
- **Phase 2:** Foundation (T008-T021) - 6-8 hours
- **Phase 3:** User Story 1 (T022-T059) - 19-24 hours
- **Phase 4:** User Story 2 (T060-T076 incl. T070a-c) - 11-13 hours
- **Phase 5:** User Story 3 (T077-T097) - 8-10 hours
- **Phase 6:** Polish (T098-T124) - 12-16 hours

---

## Key Requirements Summary

### What to Build

**Three User Stories:**
1. **Run Experiment (US1)** - Execute Taguchi L8 experiments with 4-7 variables
2. **Analyze Results (US2)** - Main effects analysis, identify optimal config
3. **Visualize Trade-offs (US3)** - Pareto frontier chart (quality vs cost)

**15 Functional Requirements:**
- FR-001 to FR-015 in `spec.md`
- Most critical: FR-001 (Taguchi L8), FR-004 (Rubric evaluation), FR-007 (Utility function)

**5 Non-Functional Requirements:**
- NFR-001: <15min mock / <30min real LLM providers
- NFR-002: Main effects <5s
- NFR-003: Pareto viz <2s
- NFR-004: Clear validation errors
- NFR-005: ≥80% test coverage for core

---

## Technology Stack

```python
# Core Dependencies (from plan.md)
LangGraph==0.2.0+      # Workflow orchestration (MANDATORY)
LiteLLM==1.0+          # Provider abstraction
Pydantic==2.0+         # Validation
NumPy==1.24+           # Taguchi math
SciPy==1.10+           # Statistics
Matplotlib==3.7+       # Visualization
PyYAML==6.0+           # Config parsing
Typer==0.9+            # CLI framework
Rich==13.0+            # Terminal UI
pytest==7.4+           # Testing
```

---

## Architecture Overview

```
tesseract_flow/
├── core/
│   ├── base_workflow.py    # BaseWorkflowService (Generic[Input, Output])
│   ├── config.py           # Pydantic models for configs
│   ├── strategies.py       # Generation strategy registry
│   └── exceptions.py       # Custom exception hierarchy
├── experiments/
│   ├── taguchi.py          # L8 array generation
│   ├── executor.py         # ExperimentExecutor
│   └── analysis.py         # Main effects computation
├── evaluation/
│   ├── rubric.py           # RubricEvaluator (LLM-as-judge)
│   ├── metrics.py          # QualityScore tracking
│   └── cache.py            # Response caching for reproducibility
├── optimization/
│   ├── utility.py          # UtilityFunction (quality/cost/time)
│   └── pareto.py           # Pareto frontier computation
├── cli/
│   ├── main.py             # Typer app entry point
│   ├── experiment.py       # experiment run/analyze commands
│   └── visualize.py        # visualize pareto command
└── workflows/
    └── code_review.py      # Example: CodeReviewWorkflow

tests/
├── unit/                   # Core algorithm tests (≥80% coverage)
├── integration/            # End-to-end workflow tests
└── fixtures/               # Test data
```

---

## Implementation Strategy

### Week 1: Foundation (Phases 1-2)
1. Create directory structure (T001-T007)
2. Implement Pydantic config models (T008-T014)
3. Create BaseWorkflowService with LangGraph integration (T015)
4. Build generation strategy registry (T016-T018)
5. Write foundation unit tests (T019-T021)

**Milestone:** Can load configs, define workflows, tests pass

### Week 2: Taguchi & Execution (Phase 3 Part 1)
1. Implement L8 array generator (T022-T027)
2. Build RubricEvaluator with LLM-as-judge (T028-T034)
3. Create UtilityFunction with normalization (T035-T046)

**Milestone:** Can generate test configs, evaluate quality

### Week 3: Complete Experiment Running (Phase 3 Part 2)
1. Build ExperimentExecutor (T039-T046)
2. Add response caching for reproducibility (T043a-T043e)
3. Create CodeReviewWorkflow example (T047-T052)
4. Build CLI experiment run command (T053-T059)

**Milestone:** Can run full L8 experiment end-to-end

### Week 4: Analysis (Phase 4)
1. Implement main effects analysis (T060-T067)
2. Build optimal config identification (T068-T070)
3. Create CLI analyze command with Rich tables (T071-T076)

**Milestone:** Can analyze results, export optimal config

### Week 5: Visualization (Phase 5)
1. Implement Pareto frontier computation (T077-T083)
2. Build matplotlib visualization (T084-T091)
3. Create CLI visualize command (T092-T097)

**Milestone:** Can generate publication-quality Pareto charts

### Week 6: Polish (Phase 6)
1. Add error handling and retries (T098-T103)
2. Polish CLI with Rich UI (T104-T108)
3. Write documentation (T109-T114)
4. Package and test distribution (T115-T124)

**Milestone:** Production-ready MVP

---

## Critical Implementation Details

### 1. BaseWorkflowService (T015)
```python
from langgraph.graph import StateGraph
from pydantic import BaseModel

class BaseWorkflowService(Generic[InputModel, OutputModel]):
    def _build_workflow(self) -> StateGraph:
        """Subclasses implement this to return LangGraph StateGraph"""
        raise NotImplementedError
    
    def run(self, input: InputModel) -> OutputModel:
        """Compiles graph, executes, tracks metrics"""
        graph = self._build_workflow()
        compiled = graph.compile()
        # Execute and track cost/latency
```

### 2. Taguchi L8 Array (T022)
```python
# Hard-coded standard L8 orthogonal array
L8_ARRAY = np.array([
    [1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 2, 2, 2, 2],
    # ... 8 rows total
])
```

### 3. Utility Function (FR-007)
```python
# Normalization: min-max across current experiment
norm_cost = (cost - min_cost) / (max_cost - min_cost) if max != min else 0.0
norm_time = (time - min_time) / (max_time - min_time) if max != min else 0.0

# Utility calculation
utility = w_quality * quality - w_cost * norm_cost - w_time * norm_time
```

### 4. Main Effects (T060-T065)
```python
# Compute average utility for each variable level
for variable in variables:
    level_1_avg = mean(utilities where variable == level_1)
    level_2_avg = mean(utilities where variable == level_2)
    effect_size = level_2_avg - level_1_avg
    contribution_pct = (effect_size / total_variation) * 100
```

### 5. Pareto Frontier (T077-T081)
```python
# Configuration A dominates B if:
# A.quality >= B.quality AND A.cost <= B.cost AND A.time <= B.time
# AND at least one inequality is strict
```

---

## Testing Requirements

**Unit Tests (≥80% coverage):**
- Taguchi array orthogonality (T026)
- Main effects calculation (T066-T067)
- Pareto frontier identification (T082-T083)
- Utility function and normalization (T045-T046)
- Config validation (T019-T020)

**Integration Tests:**
- Full experiment execution (T034, T052)
- CLI command invocations (T059, T076, T097)
- CodeReviewWorkflow end-to-end (T052)

---

## Success Criteria (from spec.md)

**Must achieve:**
- SC-001: Run 4-variable L8 experiment in <30 minutes
- SC-002: Correctly identify top contributing variable
- SC-003: Find ≥3 Pareto-optimal configs
- SC-004: Optimal config improves quality 10-30% vs baseline
- SC-005: Reproducible configs and workflow logic
- SC-006: Main effects contributions sum to ~100%
- SC-007: Clear Pareto chart with labeled axes
- SC-008: Complete code review example working

---

## Reference Files

**Read these for context:**
- `README.md` - Project overview
- `.agents` - Development process guidelines
- `CLAUDE.md` - AI assistant context
- `docs/architecture/` - Architecture principles

**Don't modify:**
- `.specify/` - Spec-Kit templates and tooling
- `.claude/` - Claude Code commands

---

## Tips for Success

1. **Follow tasks.md sequentially** - Dependencies are marked
2. **Check off tasks as completed** - Track progress
3. **Write tests alongside implementation** - Not after
4. **Reference task numbers in commits** - E.g., "feat: Implement L8 array generator [T022-T023]"
5. **Verify constitution compliance** - Run through 6 principles regularly
6. **Test with mock provider first** - Real LLM calls in integration tests only

---

## Questions While Implementing?

1. **Unclear requirement?** Check spec.md (FR-XXX) or data-model.md
2. **Architectural decision needed?** Review constitution.md and plan.md
3. **API contract unclear?** Check contracts/ directory
4. **Need example?** See quickstart.md for complete walkthrough

---

**Ready to implement? Start with `specs/001-mvp-optimizer/tasks.md` Task T001!**

Good luck! 🚀
