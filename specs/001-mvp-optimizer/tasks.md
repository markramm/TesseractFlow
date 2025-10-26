# Implementation Tasks: LLM Workflow Optimizer MVP

**Feature**: 001-mvp-optimizer | **Branch**: `001-mvp-optimizer` | **Date**: 2025-10-25

This document provides a dependency-ordered task breakdown for implementing the MVP.

---

## Task Organization

Tasks are organized by **User Story** to enable independent implementation and testing:

- **Phase 1: Setup** - Project initialization (no story label)
- **Phase 2: Foundational** - Core infrastructure (no story label)
- **Phase 3: User Story 1 (P1)** - Run Taguchi Experiment
- **Phase 4: User Story 2 (P2)** - Analyze Results
- **Phase 5: User Story 3 (P3)** - Visualize Pareto Frontier
- **Phase 6: Polish** - Error handling, docs, packaging

**Legend:**
- `[P]` = Parallelizable (can run simultaneously with other [P] tasks in same phase)
- `[US1]`, `[US2]`, `[US3]` = User Story labels
- Tasks without story labels are foundational or cross-cutting

---

## Phase 1: Setup & Project Structure

**Goal:** Initialize project with proper structure and dependencies

**Estimated Time:** 2-4 hours

- [ ] T001 - Create directory structure per plan.md specifications in tesseract_flow/
- [ ] T002 [P] - Create all `__init__.py` files for Python package structure
- [ ] T003 [P] - Set up pytest configuration in pyproject.toml with asyncio_mode and coverage
- [ ] T004 - Create tests/fixtures/ directory with placeholder experiment_results.json
- [ ] T005 - Create examples/code_review/ directory with sample code files
- [ ] T006 [P] - Set up development environment documentation in docs/development/setup.md
- [ ] T007 [P] - Create .gitignore for Python, pytest cache, coverage reports

---

## Phase 2: Core Foundation

**Goal:** Implement core types, configuration, and validation (blocks all user stories)

**Estimated Time:** 6-8 hours

### Configuration & Types

- [ ] T008 - Define core types in tesseract_flow/core/types.py (ExperimentStatus, UtilityWeights)
- [ ] T009 - Define exception hierarchy in tesseract_flow/core/exceptions.py
- [ ] T010 - Implement Variable model in tesseract_flow/core/config.py with Pydantic validation
- [ ] T011 - Implement UtilityWeights model in tesseract_flow/core/config.py
- [ ] T012 - Implement ExperimentConfig model in tesseract_flow/core/config.py with 4-7 variable validation
- [ ] T013 - Implement WorkflowConfig model in tesseract_flow/core/config.py
- [ ] T014 - Add YAML loading methods to ExperimentConfig using PyYAML

### Base Classes

- [ ] T015 - Create BaseWorkflowService abstract class in tesseract_flow/core/base_workflow.py
  - Extend Generic[InputModel, OutputModel] with Pydantic models
  - Define abstract _build_workflow(self) -> StateGraph method (LangGraph integration)
  - Implement run(input: InputModel) -> OutputModel that compiles and invokes LangGraph workflow
  - Capture execution metadata (start/end time, cost, latency)
  - Raise WorkflowExecutionError on failure
- [ ] T016 - Create GenerationStrategy protocol in tesseract_flow/core/strategies.py
- [ ] T017 - Implement StandardStrategy in tesseract_flow/core/strategies.py
- [ ] T018 - Implement strategy registry (GENERATION_STRATEGIES, get_strategy, register_strategy)

### Unit Tests for Foundation

- [ ] T019 [P] - Write unit tests for Variable validation in tests/unit/test_config.py
- [ ] T020 [P] - Write unit tests for ExperimentConfig validation in tests/unit/test_config.py
- [ ] T021 [P] - Write unit tests for strategy registry in tests/unit/test_strategies.py

**Success Criteria:** Config validation works, base classes defined, tests pass

---

## Phase 3: User Story 1 - Run Taguchi Experiment (P1)

**Goal:** User can define 4 variables, run 8 experiments, get results with quality/cost/latency

**Independent Test:** Run experiment with config.yaml, verify 8 test results generated

**Estimated Time:** 16-20 hours

### Taguchi Array Generation

- [ ] T022 [US1] - Define L8_ARRAY constant in tesseract_flow/experiments/taguchi.py
- [ ] T023 [US1] - Implement generate_l8_array() function in tesseract_flow/experiments/taguchi.py
- [ ] T024 [US1] - Implement TestConfiguration model in tesseract_flow/core/config.py
- [ ] T025 [US1] - Implement generate_test_configs() function in tesseract_flow/experiments/taguchi.py
- [ ] T026 [US1] [P] - Write unit tests for L8 array orthogonality in tests/unit/test_taguchi.py
- [ ] T027 [US1] [P] - Write unit tests for test config generation in tests/unit/test_taguchi.py

### Quality Evaluation

- [ ] T028 [US1] - Implement QualityScore and DimensionScore models in tesseract_flow/evaluation/metrics.py
- [ ] T029 [US1] - Implement RubricEvaluator class in tesseract_flow/evaluation/rubric.py
- [ ] T030 [US1] - Implement rubric prompt building with chain-of-thought in rubric.py
- [ ] T031 [US1] - Integrate LiteLLM for provider-agnostic LLM calls in rubric.py
- [ ] T032 [US1] - Implement JSON response parsing for dimension scores in rubric.py
- [ ] T033 [US1] [P] - Write unit tests for QualityScore validation in tests/unit/test_metrics.py
- [ ] T034 [US1] [P] - Write integration test for RubricEvaluator with mock LLM in tests/integration/test_evaluation.py

### Experiment Execution

- [ ] T035 [US1] - Implement TestResult model in tesseract_flow/core/config.py with utility calculation
- [ ] T036 [US1] - Implement ExperimentRun model with status transitions in tesseract_flow/core/config.py
- [ ] T037 [US1] - Implement UtilityFunction class in tesseract_flow/optimization/utility.py
- [ ] T038 [US1] - Implement metric normalization (min-max) in tesseract_flow/optimization/utility.py
  - Normalize cost and time using min-max scaling across current experiment's 8 trials
  - Formula: norm_x = (x - min_x) / (max_x - min_x), or 0.0 if max == min
  - Input: List[TestResult] from current experiment
  - Output: Normalized cost and time values for utility calculation
  - Store normalization parameters (min, max) in ExperimentRun metadata
- [ ] T039 [US1] - Implement ExperimentExecutor class in tesseract_flow/experiments/executor.py
- [ ] T040 [US1] - Implement run_single_test() method with cost/latency tracking in executor.py
- [ ] T041 [US1] - Implement run() method for full L8 experiment in executor.py
- [ ] T042 [US1] - Add progress callback support in executor.py
- [ ] T043 [US1] - Implement JSON persistence for ExperimentRun in executor.py
- [ ] T043a [US1] - Implement ExperimentMetadata model with config hash in tesseract_flow/core/config.py
  - Track configuration hash for reproducibility verification
  - Store timestamp, dependencies versions, non-determinism sources
- [ ] T043b [US1] - Create response caching interface in tesseract_flow/evaluation/cache.py
  - Define CacheBackend protocol (get, set, clear methods)
  - Support cache key generation from prompt + model + temperature
- [ ] T043c [US1] - Implement file-based response cache for deterministic test replays
  - Store LLM responses as JSON files keyed by request hash
  - Enable --use-cache and --record-cache modes
- [ ] T043d [US1] - Add --use-cache and --record-cache flags to CLI experiment run command
  - --record-cache: Save all LLM responses to cache
  - --use-cache: Replay responses from cache (skip API calls)
- [ ] T043e [US1] [P] - Write tests for cache hit/miss scenarios in tests/unit/test_cache.py
  - Test cache key generation consistency
  - Test file-based cache read/write
- [ ] T044 [US1] - Add resume capability for failed experiments in executor.py
- [ ] T045 [US1] [P] - Write unit tests for UtilityFunction in tests/unit/test_utility.py
- [ ] T046 [US1] [P] - Write unit tests for metric normalization in tests/unit/test_utility.py

### Code Review Workflow Example

- [ ] T047 [US1] - Implement CodeReviewInput and CodeReviewOutput models in tesseract_flow/workflows/code_review.py
- [ ] T048 [US1] - Implement CodeReviewWorkflow class extending BaseWorkflowService in code_review.py
- [ ] T049 [US1] - Implement code analysis using configured strategy in code_review.py
- [ ] T049a [US1] - Implement _build_workflow() returning LangGraph StateGraph in code_review.py
  - Define state dict with 'code', 'issues', 'suggestions' keys
  - Add node for code analysis using generation strategy
  - Add node for generating suggestions based on issues
  - Set entry point and edges to connect nodes
  - Return compiled StateGraph
- [ ] T050 [US1] - Create sample code files in examples/code_review/sample_code/
- [ ] T051 [US1] - Create example experiment config YAML in examples/code_review/experiment_config.yaml
- [ ] T052 [US1] [P] - Write integration test for CodeReviewWorkflow in tests/integration/test_code_review.py

### CLI for Experiment Execution

- [ ] T053 [US1] - Set up Typer app in tesseract_flow/cli/main.py
- [ ] T054 [US1] - Implement `experiment run` command in tesseract_flow/cli/experiment.py
- [ ] T055 [US1] - Add Rich progress bar for experiment execution in cli/experiment.py
- [ ] T056 [US1] - Add --verbose, --dry-run, --resume options in cli/experiment.py
- [ ] T057 [US1] - Implement JSON results output with timestamp in cli/experiment.py
- [ ] T058 [US1] - Add experiment summary display in cli/experiment.py
- [ ] T059 [US1] [P] - Write end-to-end CLI test for experiment run in tests/integration/test_cli.py

**Phase 3 Acceptance Test:**
```bash
tesseract experiment run examples/code_review/experiment_config.yaml -o results.json
# Should generate 8 test results with quality/cost/latency
```

---

## Phase 4: User Story 2 - Analyze Results (P2)

**Goal:** User can analyze experiment results, see main effects, identify optimal config

**Independent Test:** Load results.json, run analyze command, verify contribution percentages

**Estimated Time:** 10-12 hours

### Main Effects Analysis

- [ ] T060 [US2] - Implement Effect model in tesseract_flow/experiments/analysis.py
- [ ] T061 [US2] - Implement MainEffects model in tesseract_flow/experiments/analysis.py
- [ ] T062 [US2] - Implement MainEffectsAnalyzer.compute() method in analysis.py
- [ ] T063 [US2] - Implement sum-of-squares calculation in analysis.py
- [ ] T064 [US2] - Implement contribution percentage calculation in analysis.py
- [ ] T065 [US2] - Add validation that contributions sum to ~100% in analysis.py
- [ ] T066 [US2] [P] - Write unit tests with known expected outputs in tests/unit/test_main_effects.py
- [ ] T067 [US2] [P] - Write test for identical contribution edge case in tests/unit/test_main_effects.py

### Optimal Configuration Identification

- [ ] T068 [US2] - Implement identify_optimal_config() function in analysis.py
- [ ] T069 [US2] - Implement configuration comparison function in analysis.py
- [ ] T070 [US2] - Implement YAML export for optimal config in analysis.py

### Baseline Measurement & Quality Improvement

- [ ] T070a [US2] - Implement baseline tracking in ExperimentRun model in core/config.py
  - Mark first L8 test configuration as baseline
  - Store baseline quality score and configuration
- [ ] T070b [US2] - Implement quality improvement calculation in analysis.py
  - Formula: improvement_pct = (optimal_quality - baseline_quality) / baseline_quality × 100
  - Include in ExperimentResult output
- [ ] T070c [US2] [P] - Write unit test for improvement calculation in tests/unit/test_analysis.py
  - Test with known baseline and optimal values
  - Verify 10-30% improvement range for code review example

### CLI for Analysis

- [ ] T071 [US2] - Implement `analyze` command in tesseract_flow/cli/experiment.py
- [ ] T072 [US2] - Add Rich table formatting for main effects display in cli/experiment.py
- [ ] T073 [US2] - Add --format option (table, json, markdown) in cli/experiment.py
- [ ] T074 [US2] - Add --export option for optimal config YAML in cli/experiment.py
- [ ] T075 [US2] - Implement configuration comparison display in cli/experiment.py
  - Show baseline config and quality
  - Show optimal config and quality
  - Display improvement percentage with color (green if 10-30%, yellow otherwise)
- [ ] T076 [US2] [P] - Write CLI test for analyze command in tests/integration/test_cli.py

**Phase 4 Acceptance Test:**
```bash
tesseract analyze results.json --export optimal_config.yaml
# Should display:
# - Main effects table with contribution %
# - Baseline configuration and quality score
# - Optimal configuration and quality score
# - Quality improvement percentage (target: 10-30%)
# Should export optimal configuration
```

---

## Phase 5: User Story 3 - Visualize Pareto Frontier (P3)

**Goal:** User can generate Pareto chart showing quality/cost trade-offs

**Independent Test:** Load results.json, generate Pareto PNG, verify optimal points highlighted

**Estimated Time:** 8-10 hours

### Pareto Computation

- [ ] T077 [US3] - Implement ParetoPoint model in tesseract_flow/optimization/pareto.py
- [ ] T078 [US3] - Implement ParetoFrontier model in pareto.py
- [ ] T079 [US3] - Implement ParetoFrontier.compute() with sort-based algorithm in pareto.py
- [ ] T080 [US3] - Implement dominance checking logic in pareto.py
- [ ] T081 [US3] - Add budget threshold filtering in pareto.py
- [ ] T082 [US3] [P] - Write unit tests for Pareto frontier identification in tests/unit/test_pareto.py
- [ ] T083 [US3] [P] - Write test for edge cases (all dominated, single optimal) in tests/unit/test_pareto.py

### Visualization

- [ ] T084 [US3] - Implement ParetoFrontier.visualize() using matplotlib in pareto.py
- [ ] T085 [US3] - Add scatter plot with cost on X-axis, quality on Y-axis in pareto.py
- [ ] T086 [US3] - Implement bubble size for latency dimension in pareto.py
- [ ] T087 [US3] - Add highlighting for Pareto-optimal points in pareto.py
- [ ] T088 [US3] - Add budget threshold line visualization in pareto.py
- [ ] T089 [US3] - Add test number annotations to points in pareto.py
- [ ] T090 [US3] - Implement SVG/PNG/PDF export options in pareto.py
- [ ] T091 [US3] [P] - Write test for visualization generation in tests/unit/test_pareto.py

### CLI for Visualization

- [ ] T092 [US3] - Implement `visualize pareto` command in tesseract_flow/cli/visualize.py
- [ ] T093 [US3] - Add --x-axis and --y-axis options in cli/visualize.py
- [ ] T094 [US3] - Add --budget option for threshold filtering in cli/visualize.py
- [ ] T095 [US3] - Add --interactive option for plot window in cli/visualize.py
- [ ] T096 [US3] - Add console output listing Pareto-optimal configs in cli/visualize.py
- [ ] T097 [US3] [P] - Write CLI test for visualize command in tests/integration/test_cli.py

**Phase 5 Acceptance Test:**
```bash
tesseract visualize pareto results.json -o pareto.png --budget 0.01
# Should generate PNG with Pareto frontier highlighted
# Should show console output of optimal configs within budget
```

---

## Phase 6: Polish & Documentation

**Goal:** Production-ready error handling, comprehensive docs, packaging

**Estimated Time:** 12-16 hours

### Error Handling & Robustness

- [ ] T098 - Add exponential backoff retry for LLM API calls in rubric.py
- [ ] T099 - Implement comprehensive error messages with recovery suggestions in cli/
- [ ] T100 - Add validation error handling with clear user feedback in config.py
- [ ] T101 - Implement partial results saving for failed experiments in executor.py
- [ ] T102 - Add logging throughout application using Python logging module
- [ ] T103 [P] - Write tests for error scenarios in tests/unit/test_error_handling.py

### CLI Polish

- [ ] T104 - Implement `experiment status` command in cli/experiment.py
- [ ] T105 - Add global --help, --version, --log-level options in cli/main.py
- [ ] T106 - Improve error messages with emoji and colors using Rich in cli/
- [ ] T107 - Add config file validation command in cli/experiment.py
- [ ] T108 [P] - Write CLI help text tests in tests/integration/test_cli_help.py

### Documentation

- [ ] T109 [P] - Write user guide in docs/user-guide/quickstart.md (copy from specs)
- [ ] T110 [P] - Write configuration reference in docs/user-guide/configuration.md
- [ ] T111 [P] - Write results interpretation guide in docs/user-guide/interpreting-results.md
- [ ] T112 [P] - Write API documentation in docs/api/core-modules.md
- [ ] T113 [P] - Update README.md with installation, quick start, and examples
- [ ] T114 [P] - Create examples/README.md with example walkthrough

### Packaging & Distribution

- [ ] T115 - Verify pyproject.toml has all dependencies from plan.md
- [ ] T116 - Add entry points for CLI commands in pyproject.toml
- [ ] T117 - Test package installation in clean virtualenv
- [ ] T118 - Create wheel and test distribution
- [ ] T119 [P] - Set up GitHub Actions for CI/CD (optional for MVP)

### Final Integration Testing

- [ ] T120 - Run complete end-to-end workflow test with real LLM calls
- [ ] T121 - Verify all CLI commands work as documented
- [ ] T122 - Test with different LLM providers (OpenRouter, Anthropic, OpenAI)
- [ ] T123 - Validate test coverage is ≥80% for core modules
- [ ] T124 - Run performance benchmarks (15min for L8, 5s analysis, 2s viz)

**Phase 6 Acceptance:** All user stories work end-to-end, documentation complete, package installable

---

## Dependencies

### Workflow Dependencies

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundation) ← Must complete before any user stories
    ↓
Phase 3 (US1) ─┐
Phase 4 (US2) ─┼─ Can run in parallel (independent user stories)
Phase 5 (US3) ─┘
    ↓
Phase 6 (Polish) ← Requires all user stories complete
```

### Key Blocking Tasks

- **T008-T014** (Config models) block all user stories
- **T015-T018** (Base classes) block all user stories
- **T022-T025** (Taguchi) block US1
- **T028-T032** (Evaluator) block US1
- **T060-T065** (Main effects) block US2
- **T077-T081** (Pareto) block US3

### Parallel Execution Opportunities

**Within Phase 2:**
- T019, T020, T021 (all unit tests can run parallel)

**Within Phase 3 (US1):**
- T026, T027 (Taguchi tests) - parallel
- T033, T034 (Evaluation tests) - parallel
- T045, T046 (Utility tests) - parallel
- T052 (CodeReview test) - parallel with T059 (CLI test)

**Within Phase 4 (US2):**
- T066, T067 (Main effects tests) - parallel
- T070c (Baseline improvement test) - parallel
- T076 (CLI test) - parallel with documentation

**Within Phase 5 (US3):**
- T082, T083, T091 (all Pareto tests) - parallel

**Within Phase 6:**
- All documentation tasks (T109-T114) can run in parallel
- All test tasks can run in parallel once code is complete

---

## Estimated Timeline

| Phase | Tasks | Time | Cumulative |
|-------|-------|------|------------|
| Phase 1: Setup | T001-T007 (7 tasks) | 2-4 hours | 4 hours |
| Phase 2: Foundation | T008-T021 (14 tasks) | 6-8 hours | 12 hours |
| Phase 3: US1 (P1) | T022-T059 (44 tasks incl. T043a-e, T049a) | 19-24 hours | 36 hours |
| Phase 4: US2 (P2) | T060-T076 (20 tasks incl. T070a-c) | 11-13 hours | 49 hours |
| Phase 5: US3 (P3) | T077-T097 (21 tasks) | 8-10 hours | 59 hours |
| Phase 6: Polish | T098-T124 (27 tasks) | 12-16 hours | 75 hours |

**Total:** 135 tasks, 65-75 hours (~2-3 weeks full-time, or 7-9 weeks part-time)

---

## Task Completion Strategy

### Week 1-2: Core Infrastructure (Phases 1-2)
- Complete setup and foundation
- All config validation working
- Base classes defined
- Unit tests passing

**Milestone:** Can load experiment config, generate L8 array

### Week 3-4: User Story 1 (Phase 3)
- Complete experiment execution
- Quality evaluation working
- Code review example functional
- CLI for running experiments

**Milestone:** Can run full L8 experiment and get results

### Week 5-6: User Stories 2 & 3 (Phases 4-5)
- Main effects analysis
- Optimal config identification
- Pareto frontier visualization
- Complete CLI

**Milestone:** Complete analysis and visualization working

### Week 7-8: Polish (Phase 6)
- Error handling
- Documentation
- Packaging
- Final testing

**Milestone:** Production-ready MVP

---

## Success Metrics

### Code Quality
- [ ] All unit tests passing
- [ ] Integration tests passing
- [ ] Test coverage ≥80% for core modules (taguchi, analysis, pareto, utility)
- [ ] No linting errors (Ruff)
- [ ] Type checking passes (MyPy)

### Performance
- [ ] L8 experiment completes in <15 minutes
- [ ] Main effects analysis <5 seconds
- [ ] Pareto visualization <2 seconds
- [ ] Config validation <100ms

### User Experience
- [ ] All CLI commands work as documented
- [ ] Error messages are clear and actionable
- [ ] Examples run successfully
- [ ] Documentation is complete and accurate

---

## Notes

- **Tests are not explicitly requested in spec**, so unit/integration tests are included but not required for MVP completion
- **Parallel tasks** marked with [P] can be worked on simultaneously by multiple developers
- **Story labels** [US1], [US2], [US3] map to user stories in spec.md
- **File paths** are specified for each task to minimize ambiguity
- **Incremental delivery:** Each user story phase delivers independent value

---

## Next Steps

1. **Review this task breakdown** - Ensure all tasks are clear and achievable
2. **Run /speckit.analyze** - Validate consistency across spec/plan/tasks
3. **Start implementation** - Begin with Phase 1 (Setup)
4. **Track progress** - Check off tasks as completed
5. **Test continuously** - Run tests after each phase

---

**Ready to begin implementation!** Start with T001 (directory structure) and work through phases sequentially.
