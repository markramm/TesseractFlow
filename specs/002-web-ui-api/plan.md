# Implementation Plan: Web UI and API (v0.2)

**Feature ID:** 002-web-ui-api
**Version:** 0.2.0
**Created:** 2025-10-26
**Est. Duration:** 6 weeks (120-150 hours)

---

## Architecture Overview

### Technology Stack

```
Frontend:  Streamlit (Python-native web UI)
Backend:   FastAPI (async REST API)
Database:  SQLite (local) → PostgreSQL (hosted, future)
Server:    Uvicorn (ASGI)
Auth:      JWT tokens + password hashing
Real-time: WebSocket (experiment progress)
```

### Project Structure

```
tesseract_flow/
├── api/                      # NEW: FastAPI backend
│   ├── __init__.py
│   ├── main.py               # FastAPI app
│   ├── routes/
│   │   ├── experiments.py    # /api/experiments/*
│   │   ├── analysis.py       # /api/analyze/*
│   │   ├── knowledge.py      # /api/knowledge/*
│   │   └── auth.py           # /api/auth/*
│   ├── models/               # SQLAlchemy models
│   │   ├── user.py
│   │   ├── experiment.py
│   │   └── insight.py
│   ├── schemas/              # Pydantic request/response
│   │   ├── experiment.py
│   │   ├── analysis.py
│   │   └── auth.py
│   ├── dependencies.py       # Auth, DB session
│   ├── database.py           # SQLAlchemy setup
│   └── websocket.py          # Real-time updates

├── ui/                       # NEW: Streamlit web UI
│   ├── __init__.py
│   ├── app.py                # Main Streamlit app
│   ├── pages/
│   │   ├── 1_experiments.py  # Experiments list/run
│   │   ├── 2_results.py      # Results dashboard
│   │   ├── 3_knowledge.py    # Knowledge base
│   │   └── 4_profile.py      # User profile/settings
│   ├── components/
│   │   ├── charts.py         # Reusable chart components
│   │   ├── forms.py          # Config forms
│   │   └── tables.py         # Data tables
│   └── utils.py              # API client, helpers

├── cli/                      # EXISTING: v0.1 CLI (unchanged)
├── core/                     # EXISTING: Core logic (unchanged)
├── experiments/              # EXISTING: Execution (unchanged)
├── evaluation/               # EXISTING: Rubric eval (unchanged)
└── optimization/             # EXISTING: Analysis (unchanged)

tests/
├── api/                      # NEW: API endpoint tests
├── ui/                       # NEW: UI component tests
└── integration/              # EXISTING + NEW: E2E tests

alembic/                      # NEW: Database migrations
├── versions/
└── env.py
```

---

## Phase 1: Backend Foundation (Week 1-2, 30-40 hours)

### Milestone 1.1: FastAPI Setup (8-10 hours)

**Goal:** Working FastAPI server with OpenAPI docs

**Tasks:**
- [ ] Install dependencies: `fastapi`, `uvicorn`, `sqlalchemy`, `alembic`
- [ ] Create `tesseract_flow/api/main.py` with basic FastAPI app
- [ ] Set up CORS middleware (for future React migration)
- [ ] Configure logging and error handling
- [ ] Add health check endpoint: `GET /health`
- [ ] Generate OpenAPI/Swagger docs at `/docs`
- [ ] Test: `uvicorn tesseract_flow.api.main:app --reload`

**Deliverable:** FastAPI server running on `localhost:8000` with `/docs`

---

### Milestone 1.2: Database Layer (10-12 hours)

**Goal:** SQLAlchemy models + Alembic migrations

**Tasks:**
- [ ] Create `database.py` with SQLAlchemy engine/session
- [ ] Define models:
  - [ ] `User` (id, email, hashed_password, api_keys, tier, created_at)
  - [ ] `ExperimentRecord` (id, user_id, name, config, status, results, etc.)
  - [ ] `Insight` (id, category, text, confidence, votes, evidence)
- [ ] Set up Alembic for migrations
- [ ] Create initial migration: `alembic revision --autogenerate -m "initial"`
- [ ] Test migration: `alembic upgrade head`
- [ ] Write model tests (create, read, update, delete)

**Deliverable:** Working database schema with migrations

---

### Milestone 1.3: Experiments API (8-10 hours)

**Goal:** CRUD endpoints for experiments

**Endpoints:**
```python
POST   /api/experiments              # Create + run experiment
GET    /api/experiments              # List all experiments
GET    /api/experiments/{id}         # Get experiment details
GET    /api/experiments/{id}/status  # Get execution status
DELETE /api/experiments/{id}         # Delete experiment
POST   /api/experiments/{id}/resume  # Resume incomplete
```

**Tasks:**
- [ ] Create `routes/experiments.py` with CRUD operations
- [ ] Create Pydantic schemas for request/response validation
- [ ] Integrate with existing `ExperimentExecutor` (v0.1 core)
- [ ] Add background task for experiment execution
- [ ] Store results in database
- [ ] Write endpoint tests (pytest + TestClient)

**Deliverable:** Working experiment CRUD via REST API

---

### Milestone 1.4: Analysis API (4-6 hours)

**Goal:** Analysis endpoints (main effects, Pareto)

**Endpoints:**
```python
POST   /api/analyze/main-effects     # Compute main effects
POST   /api/analyze/pareto           # Generate Pareto frontier
GET    /api/analyze/optimal/{id}     # Get optimal config
```

**Tasks:**
- [ ] Create `routes/analysis.py`
- [ ] Integrate with `MainEffectsAnalyzer` (v0.1 core)
- [ ] Integrate with `ParetoFrontier` (v0.1 core)
- [ ] Return JSON + chart data
- [ ] Write endpoint tests

**Deliverable:** Analysis results via REST API

---

### Milestone 1.5: WebSocket for Real-Time Updates (4-6 hours)

**Goal:** Live experiment progress

**Tasks:**
- [ ] Create `websocket.py` with connection manager
- [ ] Add WebSocket endpoint: `WS /ws/experiments/{id}`
- [ ] Modify `ExperimentExecutor` to emit progress events
- [ ] Send updates: test started, test completed, experiment finished
- [ ] Handle client reconnection
- [ ] Write WebSocket tests

**Deliverable:** Real-time experiment progress via WebSocket

---

## Phase 2: Web UI (Week 3-4, 40-50 hours)

### Milestone 2.1: Streamlit Setup (4-6 hours)

**Goal:** Working Streamlit app with navigation

**Tasks:**
- [ ] Install `streamlit`
- [ ] Create `ui/app.py` with home page
- [ ] Configure multi-page app (Streamlit pages/)
- [ ] Add navigation sidebar
- [ ] Create API client utility (`ui/utils.py`)
- [ ] Test: `streamlit run tesseract_flow/ui/app.py`

**Deliverable:** Streamlit app with navigation

---

### Milestone 2.2: Experiments Page (12-15 hours)

**Goal:** Create and run experiments via UI

**Features:**
- Experiment list (table with status, quality Δ, cost)
- "New Experiment" button
- YAML config editor (text area)
- Visual config builder (forms for common experiments)
- "Run" button with validation
- Progress indicator during execution
- Real-time logs via WebSocket

**Tasks:**
- [ ] Create `pages/1_experiments.py`
- [ ] Fetch experiments from API: `GET /api/experiments`
- [ ] Display as sortable/filterable table
- [ ] Add YAML text area with syntax highlighting
- [ ] Add config validation: `POST /api/experiments/validate`
- [ ] Submit experiment: `POST /api/experiments`
- [ ] Connect to WebSocket for progress updates
- [ ] Show logs in real-time
- [ ] Add "Cancel" button

**Deliverable:** Full experiment creation and execution UI

---

### Milestone 2.3: Results Dashboard (15-18 hours)

**Goal:** Interactive visualization of results

**Features:**
- Main effects bar chart (interactive)
- Pareto frontier scatter plot (quality vs cost)
- Test comparison table (sortable)
- Optimal configuration display
- Export options (JSON, CSV, PNG)

**Tasks:**
- [ ] Create `pages/2_results.py`
- [ ] Fetch experiment details: `GET /api/experiments/{id}`
- [ ] Create main effects chart (Plotly or Matplotlib)
  - [ ] Interactive hover (show contribution %)
  - [ ] Click to highlight optimal level
- [ ] Create Pareto frontier scatter plot
  - [ ] Color code by test number
  - [ ] Highlight optimal point
  - [ ] Budget line filter
- [ ] Display test comparison table
  - [ ] Sort by quality, cost, latency
  - [ ] Highlight optimal config
- [ ] Add "Export Chart" button (PNG/SVG)
- [ ] Add "Download Config" button (YAML)
- [ ] Add "Run Follow-Up Experiment" button

**Deliverable:** Complete results visualization dashboard

---

### Milestone 2.4: Knowledge Base Page (6-8 hours)

**Goal:** Browse and search insights

**Features:**
- List all insights (with filtering)
- Search by keyword
- View insight details (evidence, confidence)
- Vote up/down insights
- Suggest next experiment

**Tasks:**
- [ ] Create `pages/3_knowledge.py`
- [ ] Fetch insights: `GET /api/knowledge/insights`
- [ ] Add filters: category, model, workflow, confidence
- [ ] Add search box
- [ ] Display insights as cards (text, confidence, votes)
- [ ] Add vote buttons: `POST /api/knowledge/insights/{id}/vote`
- [ ] Show evidence (experiments that support this insight)
- [ ] Add "Suggest Next Experiment" button
  - [ ] Call: `GET /api/knowledge/suggest`
  - [ ] Pre-fill config with suggestions

**Deliverable:** Knowledge base explorer UI

---

### Milestone 2.5: Reusable Components (3-5 hours)

**Goal:** Clean, maintainable UI code

**Tasks:**
- [ ] Create `components/charts.py`
  - [ ] `render_main_effects_chart(results)`
  - [ ] `render_pareto_chart(results, budget_filter)`
  - [ ] `render_test_table(results)`
- [ ] Create `components/forms.py`
  - [ ] `render_config_form()` (visual config builder)
  - [ ] `render_yaml_editor(initial_yaml)`
- [ ] Create `components/tables.py`
  - [ ] `render_experiments_table(experiments)`
  - [ ] `render_insights_table(insights)`
- [ ] Add styling (custom CSS)

**Deliverable:** Reusable, tested UI components

---

## Phase 3: Authentication (Week 5, 20-25 hours)

### Milestone 3.1: User Model & Auth Backend (8-10 hours)

**Goal:** User signup, login, JWT tokens

**Tasks:**
- [ ] Install `python-jose`, `passlib`, `python-multipart`
- [ ] Create `User` model (already done in Phase 1.2)
- [ ] Create `routes/auth.py`:
  - [ ] `POST /api/auth/signup` (create user, hash password)
  - [ ] `POST /api/auth/login` (verify credentials, return JWT)
  - [ ] `POST /api/auth/logout` (invalidate token)
  - [ ] `GET /api/auth/me` (get current user)
  - [ ] `PUT /api/auth/me/api-keys` (update LLM API keys, encrypted)
- [ ] Implement JWT token generation/verification
- [ ] Add password hashing (bcrypt via passlib)
- [ ] Encrypt API keys before storage (Fernet)
- [ ] Write auth tests

**Deliverable:** Working user authentication backend

---

### Milestone 3.2: Auth Middleware & Dependencies (4-6 hours)

**Goal:** Protect API endpoints with authentication

**Tasks:**
- [ ] Create `dependencies.py`:
  - [ ] `get_current_user()` (verify JWT, return User)
  - [ ] `get_db_session()` (dependency injection for DB)
- [ ] Add auth dependency to protected routes:
  - [ ] Experiments: require `current_user`
  - [ ] Analysis: require `current_user`
  - [ ] Knowledge: public read, authenticated write (voting)
- [ ] Add user_id to experiment records
- [ ] Filter experiments by user (multi-tenancy)
- [ ] Write integration tests

**Deliverable:** Protected API endpoints

---

### Milestone 3.3: Login/Signup UI (6-8 hours)

**Goal:** User authentication UI

**Tasks:**
- [ ] Create `pages/4_profile.py`
- [ ] Add login form (email, password)
  - [ ] Call `POST /api/auth/login`
  - [ ] Store JWT in session state
- [ ] Add signup form (email, password, confirm password)
  - [ ] Call `POST /api/auth/signup`
  - [ ] Redirect to login on success
- [ ] Add "Forgot Password" flow (future: v0.2.1)
- [ ] Add user profile page:
  - [ ] Display email, tier
  - [ ] Form to update LLM API keys
  - [ ] Call `PUT /api/auth/me/api-keys`
- [ ] Add logout button
- [ ] Update navigation to show/hide login/signup

**Deliverable:** Complete auth UI

---

### Milestone 3.4: Session Management (2-3 hours)

**Goal:** Persist auth state in Streamlit

**Tasks:**
- [ ] Store JWT token in `st.session_state`
- [ ] Add auth check to all pages
- [ ] Redirect to login if not authenticated
- [ ] Auto-refresh token before expiry
- [ ] Handle token expiration gracefully

**Deliverable:** Seamless auth experience

---

## Phase 4: Polish & Testing (Week 6, 30-35 hours)

### Milestone 4.1: Error Handling (6-8 hours)

**Goal:** Graceful error handling throughout

**Tasks:**
- [ ] Add error boundaries in Streamlit
- [ ] Display user-friendly error messages
- [ ] API error responses (standardized format)
- [ ] Validation errors (Pydantic)
- [ ] 404 handling (experiment not found)
- [ ] 401 handling (unauthorized)
- [ ] 500 handling (server error)
- [ ] Log all errors server-side
- [ ] Test error scenarios

**Deliverable:** Robust error handling

---

### Milestone 4.2: Responsive Design (4-6 hours)

**Goal:** Works on desktop and tablet

**Tasks:**
- [ ] Test on different screen sizes
- [ ] Add responsive layouts (Streamlit columns)
- [ ] Mobile-friendly navigation
- [ ] Chart responsiveness (auto-resize)
- [ ] Table scrolling on small screens

**Deliverable:** Responsive UI

---

### Milestone 4.3: End-to-End Testing (8-10 hours)

**Goal:** Full user journey tests

**Scenarios:**
- [ ] User signs up → logs in → runs experiment → views results → logs out
- [ ] User uploads config → validates → runs → resumes (simulated interruption)
- [ ] User views knowledge base → votes on insight → suggests experiment
- [ ] API integration tests (all endpoints)
- [ ] WebSocket connection tests
- [ ] Database migration tests

**Tools:**
- pytest (API tests)
- pytest-asyncio (async tests)
- Selenium or Playwright (UI tests, optional)

**Deliverable:** Comprehensive test coverage (≥70%)

---

### Milestone 4.4: Performance Optimization (4-6 hours)

**Goal:** Fast, responsive UI

**Tasks:**
- [ ] Profile API endpoints (< 500ms target)
- [ ] Add database indexes (experiment.user_id, experiment.created_at)
- [ ] Cache expensive queries (knowledge base)
- [ ] Optimize chart rendering (lazy load)
- [ ] Add loading spinners for async operations
- [ ] Compress API responses (gzip)

**Deliverable:** Fast, snappy UI

---

### Milestone 4.5: Documentation (6-8 hours)

**Goal:** Complete user and developer docs

**Tasks:**
- [ ] Update README with web UI instructions
- [ ] Create API documentation (auto-generated via OpenAPI)
- [ ] Write deployment guide:
  - [ ] Local: `tesseract serve`
  - [ ] Docker: `docker-compose up`
  - [ ] Cloud: Railway/Render/Fly.io
- [ ] Update quickstart guide
- [ ] Create video walkthrough (optional)

**Deliverable:** Complete documentation

---

### Milestone 4.6: Deployment Preparation (2-4 hours)

**Goal:** Easy deployment

**Tasks:**
- [ ] Create Dockerfile (multi-stage: API + UI)
- [ ] Create docker-compose.yml (API + UI + PostgreSQL)
- [ ] Add environment variables (.env.example)
- [ ] Create startup script: `tesseract serve` (starts both API and UI)
- [ ] Test deployment locally with Docker
- [ ] Write deployment guide for Railway/Render

**Deliverable:** Production-ready deployment

---

## Testing Strategy

### Unit Tests (≥80% coverage for new code)

**API Routes:**
- Test all endpoints (happy path + error cases)
- Test authentication flows
- Test WebSocket connections

**UI Components:**
- Test chart rendering
- Test form validation
- Test API client utilities

**Database:**
- Test model CRUD operations
- Test migrations (up + down)
- Test data integrity constraints

### Integration Tests

**End-to-End Flows:**
- Complete experiment lifecycle (create → run → analyze)
- Authentication flow (signup → login → protected resource)
- Knowledge base flow (view → vote → suggest)

**API + CLI Compatibility:**
- Ensure API can run experiments created via CLI
- Ensure CLI can read experiments created via API

### Manual Testing

**Browser Compatibility:**
- Chrome, Firefox, Safari
- Desktop + Tablet

**User Acceptance:**
- Non-technical user can run experiment
- Results are clearly explained
- Errors are actionable

---

## Risk Mitigation

### Risk 1: Streamlit Limitations
**Mitigation:** Design with React migration in mind. Keep business logic in API, UI thin.

### Risk 2: WebSocket Reliability
**Mitigation:** Implement polling fallback if WebSocket unavailable.

### Risk 3: Performance with Large Experiments
**Mitigation:** Paginate experiment list, lazy load results, add database indexes.

### Risk 4: Security (API Keys Storage)
**Mitigation:** Encrypt API keys with Fernet, never log them, use environment variables.

---

## Success Metrics

### Functional
- [ ] All 6 user stories implemented and tested
- [ ] API documentation auto-generated and complete
- [ ] ≥70% test coverage for new code
- [ ] Zero critical bugs in production

### Performance
- [ ] API response time < 500ms (p95)
- [ ] UI page load < 2 seconds
- [ ] Experiment execution time same as CLI (no overhead)
- [ ] WebSocket latency < 100ms

### Usability
- [ ] Non-technical user completes first experiment in < 10 minutes
- [ ] Results dashboard requires zero explanation
- [ ] Error messages are actionable
- [ ] 80% of beta testers complete full workflow

---

## Release Plan

### v0.2.0-alpha (End of Week 4)
- API + UI functional
- No authentication yet
- Local only (SQLite)
- Internal testing

### v0.2.0-beta (End of Week 5)
- Authentication added
- Ready for external beta testers
- Hosted demo (Railway)
- 10-20 beta users

### v0.2.0 (End of Week 6)
- All polish complete
- Documentation finished
- Public release
- SaaS soft launch (Developer tier)

---

## Dependencies & Prerequisites

**Before Starting:**
- [ ] v0.1.0 released and stable
- [ ] StoryPunk case study published (optional but helpful)
- [ ] Development environment set up (Python 3.11+)

**New Dependencies:**
```toml
# pyproject.toml additions
[project.dependencies]
fastapi = "^0.109.0"
uvicorn = "^0.27.0"
sqlalchemy = "^2.0.0"
alembic = "^1.13.0"
streamlit = "^1.30.0"
python-jose = "^3.3.0"
passlib = "^1.7.4"
python-multipart = "^0.0.6"
cryptography = "^41.0.0"  # For Fernet encryption

[project.optional-dependencies]
dev = [
    ...existing...,
    "pytest-asyncio",
    "httpx",  # For FastAPI TestClient
    "selenium",  # For UI tests (optional)
]
```

---

## Timeline Summary

```
Week 1-2:  Backend Foundation (30-40 hours)
  ├─ FastAPI setup
  ├─ Database layer
  ├─ Experiments API
  ├─ Analysis API
  └─ WebSocket

Week 3-4:  Web UI (40-50 hours)
  ├─ Streamlit setup
  ├─ Experiments page
  ├─ Results dashboard
  ├─ Knowledge base page
  └─ Reusable components

Week 5:    Authentication (20-25 hours)
  ├─ Auth backend
  ├─ Auth middleware
  ├─ Login/signup UI
  └─ Session management

Week 6:    Polish & Testing (30-35 hours)
  ├─ Error handling
  ├─ Responsive design
  ├─ End-to-end testing
  ├─ Performance optimization
  ├─ Documentation
  └─ Deployment preparation

Total:     120-150 hours over 6 weeks
```

---

## Post-Release (v0.2.1+)

**Future Enhancements:**
- Multi-user workspaces (Team tier)
- PostgreSQL migration (hosted SaaS)
- Experiment comparison (side-by-side)
- Advanced charts (trends over time)
- Export to PDF (full report)
- Integrations (GitHub Actions, Slack)
- React migration (if Streamlit proves limiting)

---

## References

- Feature Spec: `specs/002-web-ui-api/spec.md`
- v0.1 Implementation: `specs/001-mvp-optimizer/`
- FastAPI Docs: https://fastapi.tiangolo.com
- Streamlit Docs: https://docs.streamlit.io
- SQLAlchemy Docs: https://docs.sqlalchemy.org
