# Feature Spec: Web UI and API (v0.2)

**Feature ID:** 002-web-ui-api
**Version:** 0.2.0
**Status:** Planning
**Created:** 2025-10-26
**Dependencies:** 001-mvp-optimizer (v0.1.0)

---

## Overview

Extend TesseractFlow with a web-based user interface and REST API to make the platform accessible to non-technical users (product managers, business analysts) and enable programmatic access for integrations.

**Strategic Context:**
- v0.1 (CLI) targets developers and power users
- v0.2 (Web UI + API) expands market to product/business roles
- Enables SaaS freemium model with hosted knowledge base
- Foundation for Developer ($5/mo) and Team ($20/seat) tiers

---

## User Stories

### US1: Run Experiment via Web UI
**As a** product manager
**I want to** configure and run experiments through a web interface
**So that** I can optimize LLM workflows without using the command line

**Acceptance Criteria:**
- [ ] Upload or paste experiment config YAML
- [ ] Visual config builder for common experiments
- [ ] Live progress updates during experiment execution
- [ ] Real-time logs and status indicators
- [ ] Download results as JSON/CSV

**Priority:** P0 (Must-Have)

---

### US2: View Results Dashboard
**As a** business analyst
**I want to** visualize experiment results in interactive charts
**So that** I can understand trade-offs and make data-driven decisions

**Acceptance Criteria:**
- [ ] Main effects bar chart (interactive)
- [ ] Pareto frontier scatter plot (quality vs cost)
- [ ] Test comparison table (sortable, filterable)
- [ ] Optimal configuration display
- [ ] Export charts as PNG/SVG

**Priority:** P0 (Must-Have)

---

### US3: Knowledge Base Explorer
**As a** workflow optimizer
**I want to** browse and search the knowledge base
**So that** I can leverage learnings from previous experiments

**Acceptance Criteria:**
- [ ] List all insights (filterable by category, model, workflow)
- [ ] Search insights by keyword
- [ ] View insight details (evidence, confidence, votes)
- [ ] Vote up/down insights
- [ ] Suggest next experiments based on KB

**Priority:** P1 (Should-Have for v0.2)

---

### US4: Experiment History
**As a** team lead
**I want to** view history of all experiments
**So that** I can track optimization progress over time

**Acceptance Criteria:**
- [ ] List all experiments (newest first)
- [ ] Filter by workflow, date range, status
- [ ] View experiment details (config, results, insights)
- [ ] Compare multiple experiments side-by-side
- [ ] Track quality/cost trends over time

**Priority:** P1 (Should-Have for v0.2)

---

### US5: API Access for Integrations
**As a** developer
**I want to** programmatically run experiments via REST API
**So that** I can integrate TesseractFlow into CI/CD pipelines

**Acceptance Criteria:**
- [ ] POST /api/experiments (create and run)
- [ ] GET /api/experiments/:id (status and results)
- [ ] GET /api/experiments (list all)
- [ ] POST /api/analyze (run analysis on results)
- [ ] API key authentication (BYO API keys)

**Priority:** P0 (Must-Have)

---

### US6: User Authentication
**As a** SaaS user
**I want to** create an account and log in
**So that** my experiments and insights are private and persistent

**Acceptance Criteria:**
- [ ] Sign up with email/password
- [ ] Log in with email/password
- [ ] Password reset flow
- [ ] User profile page (API keys, settings)
- [ ] BYO LLM API key storage (encrypted)

**Priority:** P0 (Must-Have for SaaS)

---

## Technical Architecture

### Stack Choices

**Backend:**
- **FastAPI** - Async Python web framework
  - Automatic OpenAPI docs
  - Pydantic validation (already using)
  - WebSocket support (real-time updates)
  - Native async/await (matches LiteLLM)

**Frontend:**
- **Streamlit** - Rapid prototyping, Python-native
  - Pro: Fastest to ship (pure Python, no React needed)
  - Pro: Built-in components (charts, tables, forms)
  - Pro: Auto-refresh and state management
  - Con: Less customizable than React
  - Con: Not ideal for multi-user apps

**Alternative: React + Vite** (if Streamlit proves limiting)
- Pro: Full control over UX
- Pro: Better for complex interactions
- Con: Slower to build (separate frontend/backend)
- Con: Need to learn/maintain TypeScript

**Decision:** Start with **Streamlit** for v0.2.0, migrate to React in v0.3 if needed.

**Database:**
- **SQLite** - Local file-based (v0.2.0 single-user)
- **PostgreSQL** - Hosted database (v0.2.1+ multi-user SaaS)

**Deployment:**
- **Local:** `tesseract serve` (Uvicorn + Streamlit)
- **Hosted:** Railway/Render/Fly.io (future SaaS)

---

### System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Web Browser                          │
│  ┌──────────────────┐        ┌────────────────────┐   │
│  │  Streamlit UI    │◄──────►│   REST API Client  │   │
│  │  (Port 8501)     │        │   (JavaScript)     │   │
│  └────────┬─────────┘        └──────────┬─────────┘   │
└───────────┼────────────────────────────┼───────────────┘
            │                            │
            │ HTTP                       │ HTTP/WebSocket
            │                            │
┌───────────▼────────────────────────────▼───────────────┐
│              FastAPI Backend (Port 8000)               │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │
│  │   /api/*     │  │  /ws/*       │  │   /auth/*   │  │
│  │  (REST)      │  │ (WebSocket)  │  │  (Auth)     │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬──────┘  │
│         │                  │                  │         │
│  ┌──────▼──────────────────▼──────────────────▼──────┐ │
│  │           TesseractFlow Core (v0.1)               │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │ │
│  │  │Executor  │ │Analyzer  │ │ Knowledge Base   │  │ │
│  │  └──────────┘ └──────────┘ └──────────────────┘  │ │
│  └───────────────────────────────────────────────────┘ │
└────────────────────────────┬───────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │   SQLite DB     │
                    │  (experiments,  │
                    │   insights)     │
                    └─────────────────┘
```

---

### API Endpoints

#### Experiments

```
POST   /api/experiments              Create and run experiment
GET    /api/experiments              List all experiments
GET    /api/experiments/:id          Get experiment details
GET    /api/experiments/:id/status   Get execution status
DELETE /api/experiments/:id          Delete experiment
POST   /api/experiments/:id/resume   Resume incomplete experiment
```

#### Analysis

```
POST   /api/analyze/main-effects     Compute main effects
POST   /api/analyze/pareto           Generate Pareto frontier
GET    /api/analyze/optimal/:id      Get optimal configuration
```

#### Knowledge Base

```
GET    /api/knowledge/insights       List all insights
GET    /api/knowledge/insights/:id   Get insight details
POST   /api/knowledge/insights/:id/vote  Vote up/down
GET    /api/knowledge/suggest        Suggest next experiment
```

#### Authentication

```
POST   /api/auth/signup              Create account
POST   /api/auth/login               Login
POST   /api/auth/logout              Logout
GET    /api/auth/me                  Get current user
PUT    /api/auth/me/api-keys         Update LLM API keys
```

#### WebSocket

```
WS     /ws/experiments/:id           Real-time experiment updates
```

---

### Data Model Extensions

**New Tables:**

```python
# Users (for SaaS)
class User(BaseModel):
    id: UUID
    email: EmailStr
    hashed_password: str
    created_at: datetime
    api_keys: dict[str, str]  # Encrypted: {provider: key}
    tier: Literal["free", "developer", "team", "org"]

# Experiments (persistent)
class ExperimentRecord(BaseModel):
    id: UUID
    user_id: UUID | None  # None for local CLI usage
    name: str
    config: dict  # Full YAML config
    status: Literal["running", "completed", "failed", "cancelled"]
    started_at: datetime
    completed_at: datetime | None
    results: list[TestResult] | None
    analysis: MainEffectsResult | None
    pareto: ParetoFrontier | None
    error: str | None

# Knowledge Base Insights
class Insight(BaseModel):
    id: UUID
    category: str  # "model", "workflow", "context", etc.
    text: str
    confidence: float  # 0.0-1.0
    votes: int
    evidence: list[InsightEvidence]
    created_at: datetime

class InsightEvidence(BaseModel):
    experiment_id: UUID
    contribution: float | None  # Main effect %
    notes: str | None
```

---

## UI Wireframes

### 1. Home Page

```
┌─────────────────────────────────────────────────────────┐
│  TesseractFlow                    [Login] [Sign Up]     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│    Lean LLM Optimization for Every Team                │
│    Optimize workflows in 10 minutes for $0.40          │
│                                                         │
│    [Run Your First Experiment]  [View Docs]            │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Recent Experiments                              │   │
│  ├──────────┬──────────┬─────────┬──────────────────┤   │
│  │ Name     │ Workflow │ Status  │ Quality Δ        │   │
│  ├──────────┼──────────┼─────────┼──────────────────┤   │
│  │ Scene v3 │ CodeRev  │ ✓ Done  │ +16.9% (+$0.40) │   │
│  │ Scene v2 │ CodeRev  │ ✓ Done  │ +8.2%  (+$0.40) │   │
│  └──────────┴──────────┴─────────┴──────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

### 2. New Experiment Page

```
┌─────────────────────────────────────────────────────────┐
│  ← Back to Experiments                                  │
├─────────────────────────────────────────────────────────┤
│  New Experiment                                         │
│                                                         │
│  ○ Config Builder (Visual)   ● Upload YAML             │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ # Code Review Experiment                        │   │
│  │ experiment:                                      │   │
│  │   name: "Scene Generation v4"                   │   │
│  │   workflow_class: "CodeReviewWorkflow"          │   │
│  │                                                  │   │
│  │ variables:                                       │   │
│  │   - name: "model_tier"                          │   │
│  │     level_1: "budget"                           │   │
│  │     level_2: "premium"                          │   │
│  │ ...                                              │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  [Validate Config]  [Run Experiment]                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

### 3. Experiment Running Page

```
┌─────────────────────────────────────────────────────────┐
│  ← Back                Scene Generation v4   [Cancel]   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Progress: Test 3/8 (37%)                              │
│  ████████████░░░░░░░░░░░░░░░░                          │
│                                                         │
│  Current Test:                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Test 3: budget + full_module + standard + 0.7  │   │
│  │ Status: Generating scene...                     │   │
│  │ Quality: Evaluating...                          │   │
│  │ Cost: $0.023                                     │   │
│  │ Time: 8.2s                                       │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Recent Logs:                                           │
│  ┌─────────────────────────────────────────────────┐   │
│  │ [14:32:15] Test 2 completed (quality: 78.5)    │   │
│  │ [14:32:16] Starting test 3...                  │   │
│  │ [14:32:18] Workflow initialized                │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

### 4. Results Dashboard

```
┌─────────────────────────────────────────────────────────┐
│  Scene Generation v4                    [Export] [Share]│
├─────────────────────────────────────────────────────────┤
│  Completed: 2025-10-26 14:35  │  Tests: 8/8 ✓           │
│  Quality Δ: +16.9%             │  Cost: $0.38           │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Main Effects                                   │   │
│  │  ┌─────────────────────────────────────┐        │   │
│  │  │                                     │        │   │
│  │  │  context_strategy     ████████ 48% │        │   │
│  │  │  model_tier           ██████ 35%   │        │   │
│  │  │  generation_strategy  ██ 12%       │        │   │
│  │  │  temperature          █ 5%         │        │   │
│  │  │                                     │        │   │
│  │  └─────────────────────────────────────┘        │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Pareto Frontier (Quality vs Cost)              │   │
│  │  ┌─────────────────────────────────────┐        │   │
│  │  │  100│                                │        │   │
│  │  │     │       ●← Test 7 (Optimal!)    │        │   │
│  │  │   85│    ●                           │        │   │
│  │  │   Q │  ●                             │        │   │
│  │  │   u │●                               │        │   │
│  │  │   a 70│                              │        │   │
│  │  │   l │   $0.10    $0.30    $0.50     │        │   │
│  │  │     │         Cost                   │        │   │
│  │  └─────────────────────────────────────┘        │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Optimal Configuration:                                 │
│  • model_tier: budget                                   │
│  • context_strategy: full_module                        │
│  • generation_strategy: chain_of_thought               │
│  • temperature: 0.7                                     │
│                                                         │
│  [Download Config] [Run Follow-Up Experiment]          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

### 5. Knowledge Base Page

```
┌─────────────────────────────────────────────────────────┐
│  Knowledge Base                          [Search: ___]  │
├─────────────────────────────────────────────────────────┤
│  Filters: [All Categories ▼] [All Models ▼] [Sort ▼]   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Full module context better than file-only      │   │
│  │  Category: Context Strategy  │  Confidence: 95% │   │
│  │  Votes: ↑ 3                   │  Evidence: 3    │   │
│  │                                                  │   │
│  │  "Consistently improves quality by 40-50%       │   │
│  │   across code review workflows"                 │   │
│  │                                                  │   │
│  │  [↑ Vote Up] [↓ Vote Down] [View Evidence]     │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Haiku responds well to XML-formatted prompts   │   │
│  │  Category: Model Insights     │  Confidence: 85%│   │
│  │  Votes: ↑ 2                   │  Evidence: 2    │   │
│  │  [↑ Vote Up] [↓ Vote Down] [View Evidence]     │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  [Suggest Next Experiment Based on KB]                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Success Criteria

### Functional Requirements
- ✅ Users can run complete L8 experiment via web UI
- ✅ Real-time progress updates during execution
- ✅ Interactive visualization of main effects and Pareto frontier
- ✅ Knowledge base browsing and voting
- ✅ REST API supports all core operations
- ✅ Authentication with encrypted API key storage

### Non-Functional Requirements
- ✅ Web UI loads in <2 seconds
- ✅ Experiment execution time same as CLI (no overhead)
- ✅ API response time <500ms for most endpoints
- ✅ Supports 10+ concurrent experiments (for future multi-user)
- ✅ Works on desktop and tablet (responsive design)

### User Acceptance
- ✅ Non-technical user can run experiment without docs
- ✅ Results dashboard clearly communicates insights
- ✅ API documentation auto-generated (OpenAPI/Swagger)
- ✅ 80% of test users successfully complete first experiment

---

## Implementation Phases

### Phase 1: Backend API (Week 1-2)
- FastAPI project setup
- REST API endpoints (experiments, analysis)
- SQLite database integration
- WebSocket for real-time updates
- API documentation (Swagger)

### Phase 2: Frontend UI (Week 3-4)
- Streamlit app setup
- Experiment configuration page
- Running experiment page (progress + logs)
- Results dashboard (charts + tables)
- Knowledge base browser

### Phase 3: Authentication (Week 5)
- User signup/login
- API key storage (encrypted)
- User profile page
- Session management

### Phase 4: Polish & Testing (Week 6)
- Error handling and validation
- Responsive design
- End-to-end testing
- Performance optimization
- Documentation

---

## Open Questions

1. **Streamlit vs React?**
   - Start with Streamlit for speed, evaluate after v0.2.0 beta
   - React migration in v0.3 if needed

2. **Local vs Hosted First?**
   - Support both: `tesseract serve` (local) and hosted SaaS
   - Local SQLite for dev, PostgreSQL for production

3. **Pricing Tiers?**
   - Free: Local only, no cloud KB
   - Developer ($5/mo): Hosted KB, 10 experiments/mo
   - Team ($20/seat): Shared KB, unlimited experiments

4. **Real-time vs Polling?**
   - Use WebSocket for real-time updates (experiment progress)
   - Fallback to polling if WebSocket unavailable

---

## Dependencies

**New Python Packages:**
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `streamlit` - Web UI
- `sqlalchemy` - ORM for database
- `alembic` - Database migrations
- `python-jose` - JWT tokens
- `passlib` - Password hashing
- `python-multipart` - File uploads

**Infrastructure:**
- SQLite (local dev)
- PostgreSQL (hosted SaaS, future)
- Railway/Render/Fly.io (deployment, future)

---

## Timeline Estimate

**Total: 6 weeks (120-150 hours)**

- Phase 1 (Backend): 30-40 hours
- Phase 2 (Frontend): 40-50 hours
- Phase 3 (Auth): 20-25 hours
- Phase 4 (Polish): 30-35 hours

**Target Release:** v0.2.0 by December 2025

---

## References

- v0.1 CLI: `specs/001-mvp-optimizer/`
- Iteration Patterns: `docs/iteration-patterns.md`
- DSPy Integration: `docs/dspy-integration-research.md`
- Conversation Summary: `docs/CONVERSATION_SUMMARY_2025_10_26.md`
