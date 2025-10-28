# TesseractFlow Roadmap

## Vision

TesseractFlow is a **rapid LLM optimization framework** using Taguchi Design of Experiments to identify high-impact configuration changes (>3% utility improvement) with minimal cost and time investment.

**Core Philosophy**: 95% of the insights for 6% of the cost compared to exhaustive testing.

---

## Current Status (v0.2.0)

### ✅ Completed Features

#### Core Framework
- [x] **Taguchi L8 Orthogonal Arrays**: 8-test designs for 4-7 variables, 2 levels each
- [x] **Statistical Replications**: n=1 to n=100 support with automatic averaging
- [x] **Main Effects Analysis**: Contribution percentages showing variable importance
- [x] **Standard Deviations**: Computed across replications for statistical confidence
- [x] **Utility Function**: Configurable quality/cost/time trade-offs
- [x] **Rubric-Based Evaluation**: Custom multi-dimensional quality metrics
- [x] **LLM-as-Judge**: Automated quality scoring with custom rubrics
- [x] **Experiment Persistence**: JSON serialization with resume capability
- [x] **CLI Interface**: Full command-line workflow for run/analyze/export

#### Validation & Testing
- [x] **160-test validation suite**: 4 fiction writing experiments × 40 runs (n=5)
- [x] **Replications feature validated**: Detects 3%+ effects with n=5
- [x] **Pydantic validation fixed**: Supports unlimited test configurations
- [x] **Analysis module enhanced**: Handles replicated experiments

#### Cost Efficiency
- [x] **$0.03 per experiment** (8 tests × n=5, using DeepSeek R1)
- [x] **8-20 minute runtime** per experiment
- [x] **50-94% cost savings** vs. full factorial
- [x] **Caching support**: Reduces duplicate LLM calls

### 📊 Validated Results

| Experiment | Dominant Variable | Contribution % | Effect Size | Optimal Config |
|------------|------------------|----------------|-------------|----------------|
| Fiction Scene Generation | context_depth | 81.2% | -1.0% | minimal context |
| Dialogue Enhancement | temperature | 54.1% | -4.0% | temp 0.6 |
| Dialogue Enhancement | voice_emphasis | 36.6% | -3.3% | subtle |
| Character Development | output_format | 68.1% | +4.4% | structured JSON |
| Progressive Discovery | generation_strategy | 78.7% | -6.8% | standard (not CoT) |

**Key Learnings**:
- Chain-of-thought is task-dependent: helps analytical work, hurts exploration
- Temperature effects vary wildly by task (critical for dialogue, irrelevant for character dev)
- Structured outputs significantly improve tracking tasks
- Subtlety beats explicitness in creative writing

---

## Short-Term Roadmap (Q1 2025)

### Priority 1: Variable Count Flexibility

**Problem**: Currently requires exactly 4 variables per experiment
**Goal**: Support 4-7 variables as advertised in L8 documentation

**Tasks**:
- [ ] Update experiment config validation to accept 4-7 variables
- [ ] Test L8 array column assignment for 5, 6, 7 variable experiments
- [ ] Validate orthogonal properties maintained across variable counts
- [ ] Add CLI validation with helpful error messages
- [ ] Update documentation with examples for each variable count

**Acceptance Criteria**:
```yaml
# Should work with 4 variables
variables:
  - name: temperature
    level_1: 0.5
    level_2: 0.9
  - name: strategy
    level_1: standard
    level_2: chain_of_thought
  - name: context
    level_1: minimal
    level_2: full
  - name: style
    level_1: concise
    level_2: lyrical

# Should also work with 7 variables
variables:
  - name: temperature
    level_1: 0.5
    level_2: 0.9
  - name: strategy
    level_1: standard
    level_2: chain_of_thought
  - name: context
    level_1: minimal
    level_2: full
  - name: style
    level_1: concise
    level_2: lyrical
  - name: revision
    level_1: refine
    level_2: regenerate
  - name: examples
    level_1: 0
    level_2: 3
  - name: format
    level_1: freeform
    level_2: structured
```

**Estimated Effort**: 4-6 hours
**Value**: Unlocks full L8 capacity (94% cost savings for 7-variable experiments)

### Priority 2: Statistical Enhancements

**Goal**: Display standard deviations and confidence metrics in CLI output

**Tasks**:
- [ ] Add `--show-statistics` flag to analyze command
- [ ] Display std_level_1 and std_level_2 in effect tables
- [ ] Show coefficient of variation (CV%) for each variable
- [ ] Add "certainty" indicator (high/medium/low based on std/effect ratio)
- [ ] Include replications count in analysis header

**Example Output**:
```
Main Effects Analysis (n=5 replications)

Variable: temperature
  Level 1 (0.5): 0.723 ± 0.012 (CV: 1.7%)
  Level 2 (0.9): 0.683 ± 0.018 (CV: 2.6%)
  Effect Size: -0.040 (certainty: HIGH)
  Contribution: 54.1%
```

**Estimated Effort**: 3-4 hours
**Value**: Better understanding of result reliability

### Priority 3: Documentation

**Goal**: Comprehensive user and developer documentation

**Tasks**:
- [ ] **User Guide**:
  - [ ] Quickstart tutorial
  - [ ] Experiment design best practices
  - [ ] Interpreting results guide
  - [ ] Troubleshooting common issues
- [ ] **API Reference**:
  - [ ] Core module documentation
  - [ ] Workflow extension guide
  - [ ] Custom rubric creation
- [ ] **Case Studies**:
  - [ ] Fiction writing optimization (completed experiments)
  - [ ] Code review optimization
  - [ ] Comparative analysis vs. other methods

**Estimated Effort**: 12-16 hours
**Value**: Essential for user adoption

---

## Medium-Term Roadmap (Q2 2025)

### Taguchi L16 Support

**Goal**: Support 5-15 variables with interaction detection

**Capabilities**:
- 16-test configurations (2× L8)
- Detect 2-way interaction effects
- Higher resolution, less confounding
- ~$0.06 per experiment (2× L8 cost)

**Use Cases**:
- Testing 8+ variables simultaneously
- Detecting interaction effects (e.g., "Does CoT effectiveness depend on temperature?")
- Follow-up experiments after L8 identifies confusing results

**Tasks**:
- [ ] Implement L16 orthogonal array generation
- [ ] Update analysis module for interaction detection
- [ ] Add `--array-type` CLI flag (l8|l16)
- [ ] Validate interaction calculation correctness
- [ ] Update cost estimation for L16

**Estimated Effort**: 20-24 hours
**Value**: Handles more complex experimental scenarios

### Full Factorial Deep Dive

**Goal**: After L8 identifies top 2-3 variables, run exhaustive tests on just those

**Example Workflow**:
```bash
# Phase 1: L8 screening (7 variables)
tesseract experiment run config.yaml --output results.json

# Analysis shows temperature (60%) and context (30%) dominate
tesseract analyze results.json
# Recommends: "Run full factorial on temperature × context"

# Phase 2: Full factorial on top 2 variables
tesseract experiment run --follow-up results.json \
  --variables temperature,context \
  --mode full_factorial \
  --output deep_dive.json
```

**Tasks**:
- [ ] Add `--mode full_factorial` option
- [ ] Generate all combinations for selected variables
- [ ] Hold other variables at optimal values from L8
- [ ] Create response surface visualization
- [ ] Add `--follow-up` flag to inherit from previous experiment

**Estimated Effort**: 16-20 hours
**Value**: Fine-tuning after exploration

### Bayesian Optimization Integration

**Goal**: Use Bayesian methods to optimize continuous variables after Taguchi identifies important ones

**Example Workflow**:
```bash
# Phase 1: L8 identifies temperature as critical (2 levels: 0.5, 0.9)
tesseract experiment run config.yaml --output l8_results.json

# Phase 2: Bayesian optimization finds optimal temperature between 0.5 and 0.9
tesseract experiment optimize l8_results.json \
  --variable temperature \
  --range 0.5:0.9 \
  --trials 15 \
  --output bayesian_results.json
```

**Dependencies**: GPyOpt or Optuna integration

**Tasks**:
- [ ] Add `optimize` subcommand
- [ ] Integrate Bayesian optimization library
- [ ] Support continuous variable ranges
- [ ] Acquisition function selection (EI, UCB, etc.)
- [ ] Convergence visualization

**Estimated Effort**: 24-32 hours
**Value**: Precision tuning for critical variables

---

## Long-Term Roadmap (Q3-Q4 2025)

### Multi-Level Support

**Goal**: Test 3+ levels per variable (not just binary low/high)

**Example**:
```yaml
variables:
  - name: temperature
    levels: [0.3, 0.5, 0.7, 0.9]  # 4 levels instead of 2
```

**Arrays**: L27, L18, L12 (mixed-level designs)

**Use Cases**:
- Mapping response curves
- Finding optimal temperature in continuous range
- Testing multiple prompt styles

**Estimated Effort**: 32-40 hours

### Interactive Dashboards

**Goal**: Web UI for experiment tracking and visualization

**Features**:
- Real-time experiment monitoring
- Interactive Pareto plots (quality vs. cost)
- Main effects charts
- Response surface 3D plots
- Experiment history tracking

**Tech Stack**: Streamlit or Gradio

**Estimated Effort**: 40-60 hours

### AutoML-Style Recommendations

**Goal**: Automatically suggest next experiments based on results

**Example**:
```bash
tesseract analyze results.json --suggest-next
```

Output:
```
Based on your results:
- temperature and context dominate (90% combined contribution)
- Recommendation 1: Run full factorial on temperature × context (4 tests)
- Recommendation 2: Test 4 temperature levels via Bayesian optimization (15 trials)
- Recommendation 3: Investigate temperature × prose_style interaction via L16 (16 tests)
```

**Estimated Effort**: 24-32 hours

### Model Comparison Framework

**Goal**: Compare multiple LLM models systematically

**Example**:
```yaml
models_to_test:
  - openrouter/deepseek/deepseek-chat
  - openrouter/anthropic/claude-3.5-sonnet
  - openrouter/openai/gpt-4
  - openrouter/google/gemini-2.0-flash

# Run L8 experiment with each model, compare results
```

**Tasks**:
- [ ] Add `models` array to experiment config
- [ ] Run same L8 experiment across all models
- [ ] Comparative analysis showing model × variable interactions
- [ ] Cost-benefit matrix across models

**Estimated Effort**: 16-20 hours
**Value**: Answer "Which model is best for my task?"

---

## Research Directions

### Adaptive Sampling

**Idea**: Use early test results to intelligently select which tests to run next

**Benefits**:
- Potentially reduce from 8 tests to 5-6 tests
- Focus sampling on high-uncertainty regions
- Faster convergence to optimal config

**Challenges**:
- Breaks orthogonal design properties
- Harder to interpret contribution percentages
- Requires real-time analysis during execution

### Transfer Learning for Experiments

**Idea**: Use results from similar experiments to initialize new ones

**Example**:
- Fiction scene generation experiment finds context_depth dominates
- Use that insight to initialize dialogue enhancement experiment
- Potentially skip testing context_depth again

**Benefits**:
- Reduce redundant testing
- Build knowledge base of "what usually matters"

**Challenges**:
- Task similarity metrics needed
- Risk of incorrect transfer

---

## Non-Goals

**Explicitly out of scope**:

1. **Real-time inference optimization**: TesseractFlow is for experimental design, not production serving
2. **Model training/fine-tuning**: Focus is on prompt engineering and configuration, not model weights
3. **Human evaluation platforms**: Use LLM-as-judge; no crowdsourcing UI planned
4. **General-purpose ML experiment tracking**: Not competing with MLflow/Weights & Biases
5. **Multi-objective optimization beyond utility**: Single scalar utility is sufficient for most use cases

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development workflow.

**High-priority contribution areas**:
1. Variable count flexibility (Priority 1)
2. Statistical enhancements (Priority 2)
3. Documentation and examples
4. L16 array implementation
5. Additional workflow examples

---

## Version History

### v0.2.0 (Current - January 2025)
- ✅ Statistical replications (n=1 to n=100)
- ✅ Main effects analysis with standard deviations
- ✅ 160-test validation across 4 fiction writing experiments
- ✅ Pydantic validation fixes for unlimited configurations
- ✅ Enhanced analysis module for replicated experiments

### v0.1.0 (December 2024)
- ✅ Initial Taguchi L8 implementation
- ✅ Rubric-based evaluation
- ✅ CLI interface
- ✅ JSON persistence
- ✅ Example workflows (code review, fiction writing)

### v0.3.0 (Planned - Q1 2025)
- [ ] Variable count flexibility (4-7 variables)
- [ ] Statistical enhancements in CLI output
- [ ] Comprehensive documentation
- [ ] Additional example experiments

### v0.4.0 (Planned - Q2 2025)
- [ ] Taguchi L16 support
- [ ] Full factorial deep dive
- [ ] Bayesian optimization integration
- [ ] Response surface visualization

---

## Success Metrics

**Adoption Goals**:
- 100+ GitHub stars by Q2 2025
- 10+ external users running experiments by Q3 2025
- 3+ contributed workflow examples by Q4 2025

**Technical Goals**:
- <$0.05 per L8 experiment (current: $0.03 ✅)
- <30 minutes per experiment (current: 8-20m ✅)
- Support 100+ replications without performance degradation
- 95%+ test coverage across core modules

**Research Goals**:
- Publish case study: "Optimizing LLM Fiction Writing with Taguchi Methods"
- Benchmark against other LLM optimization frameworks
- Validate transfer learning hypothesis across 20+ task pairs
