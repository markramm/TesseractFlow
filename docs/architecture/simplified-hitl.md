# Simplified HITL Architecture: Workflows as Boundaries

**Date:** 2025-10-25
**Key Insight:** Human-in-the-loop happens BETWEEN workflows, not WITHIN them
**Impact:** Eliminates need for Temporal, checkpointing, pause/resume complexity

---

## The Breakthrough Insight

### ❌ **Old Thinking:** HITL Within Workflows

```
Single Long-Running Workflow:
┌────────────────────────────────────────────────┐
│  Workflow: Scene Drafting with Approval       │
├────────────────────────────────────────────────┤
│  1. Generate draft                             │
│  2. Save draft                                 │
│  3. ⏸️  PAUSE - Wait for human approval        │
│     (Need: Temporal/checkpointing/signals)     │
│  4. Resume - Load feedback                     │
│  5. Apply revisions                            │
│  6. Finalize                                   │
└────────────────────────────────────────────────┘

Problems:
- Need complex orchestration (Temporal)
- Pause/resume state management
- Long-running processes
- Event/signal handling
```

### ✅ **New Thinking:** HITL Between Workflows

```
Two Simple Workflows with Human Review Between:

Workflow 1: Generate Draft
┌────────────────────────────────────────────────┐
│  1. Generate draft                             │
│  2. Evaluate quality                           │
│  3. Save to database (status: pending_review)  │
│  4. Return draft_id                            │
│  ✅ COMPLETE (10-60 seconds)                   │
└────────────────────────────────────────────────┘
                    ↓
        (Human reviews at leisure)
        Database: {draft_id, status, feedback}
                    ↓
Workflow 2: Apply Feedback
┌────────────────────────────────────────────────┐
│  1. Load draft + feedback from DB              │
│  2. Apply revisions based on feedback          │
│  3. Re-evaluate quality                        │
│  4. Save final version                         │
│  ✅ COMPLETE (10-60 seconds)                   │
└────────────────────────────────────────────────┘

Benefits:
- ✅ No pause/resume needed
- ✅ No complex orchestration
- ✅ Simple synchronous workflows
- ✅ Human reviews asynchronously
- ✅ Works with ANY framework
```

---

## What This Changes

### **Infrastructure Simplified**

| Component | Old Approach | New Approach |
|-----------|--------------|--------------|
| **Workflow Engine** | Temporal (complex) | LangGraph (simple) |
| **State Management** | Checkpointing/signals | Database rows |
| **Process Queue** | Temporal queues | Simple task queue (or none!) |
| **Pause/Resume** | Built into workflows | Not needed |
| **Human Review** | Workflow waits | Database polling/webhooks |

**Net Result:** 80% less infrastructure complexity

---

### **Architecture Comparison**

**Old (Complex):**
```
Temporal Server
  ├── Workflow Definition (pause/resume logic)
  ├── Activity Workers
  ├── Signal Handlers
  └── Checkpoint Storage

Database
  └── Workflow state snapshots

UI
  ├── Pending approvals queue
  └── Signal sender (resume workflow)
```

**New (Simple):**
```
Database
  ├── workflows table (status, results)
  ├── approvals table (pending reviews)
  └── Standard CRUD

API (FastAPI/Flask)
  ├── POST /workflows/run (start workflow 1)
  ├── GET /approvals/pending (list reviews)
  └── POST /approvals/{id}/approve (trigger workflow 2)

Optional: Simple task queue (Celery/RQ)
  └── For background execution
```

---

## Approval Queue Pattern

### Database Schema

```sql
-- Workflows table
CREATE TABLE workflows (
    id UUID PRIMARY KEY,
    type VARCHAR(50),          -- 'generate_draft', 'apply_feedback'
    status VARCHAR(20),        -- 'running', 'completed', 'failed'
    input JSONB,               -- Workflow input
    output JSONB,              -- Workflow output
    created_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Approvals table
CREATE TABLE approvals (
    id UUID PRIMARY KEY,
    workflow_id UUID REFERENCES workflows(id),
    status VARCHAR(20),        -- 'pending', 'approved', 'rejected'

    -- What needs review
    artifact_type VARCHAR(50), -- 'draft', 'config', 'experiment_results'
    artifact_id UUID,
    artifact_data JSONB,       -- The thing to review

    -- Human feedback
    reviewer_id UUID,
    approved BOOLEAN,
    feedback TEXT,
    reviewed_at TIMESTAMP,

    -- Follow-up workflow
    next_workflow_type VARCHAR(50), -- 'apply_feedback', 'deploy_config'
    next_workflow_input JSONB,

    created_at TIMESTAMP
);

-- Index for pending queue
CREATE INDEX idx_approvals_pending
ON approvals(status, created_at)
WHERE status = 'pending';
```

### API Flow

**1. User requests draft generation:**
```bash
POST /api/workflows/generate-draft
{
  "story_id": 12,
  "scene_shortname": "s01_opening",
  "prompt": "..."
}

Response:
{
  "workflow_id": "wf-123",
  "status": "running"
}
```

**2. Workflow completes, creates approval:**
```python
# Inside generate_draft workflow
draft = await generate_text(...)
quality_score = await evaluate_quality(draft)

# Save workflow result
workflow_result = {
    "draft": draft,
    "quality_score": quality_score
}
db.workflows.update(workflow_id, {
    "status": "completed",
    "output": workflow_result
})

# Create approval request
approval = db.approvals.create({
    "workflow_id": workflow_id,
    "status": "pending",
    "artifact_type": "draft",
    "artifact_data": {
        "draft_text": draft,
        "quality_score": quality_score
    },
    "next_workflow_type": "apply_feedback",
    "next_workflow_input": {
        "draft_id": draft_id,
        "story_id": story_id
    }
})

# Notify human (email/Slack/webhook)
notify_reviewer(approval.id)
```

**3. Human reviews in UI:**
```bash
GET /api/approvals/pending

Response:
{
  "approvals": [
    {
      "id": "app-456",
      "workflow_id": "wf-123",
      "artifact_type": "draft",
      "artifact_data": {
        "draft_text": "...",
        "quality_score": 85
      },
      "created_at": "2025-10-25T10:30:00Z"
    }
  ]
}
```

**4. Human approves with feedback:**
```bash
POST /api/approvals/app-456/approve
{
  "approved": true,
  "feedback": "Needs more emotional depth in the opening paragraph"
}

Response:
{
  "approval_id": "app-456",
  "next_workflow_id": "wf-789",
  "status": "approved"
}
```

**5. System triggers next workflow:**
```python
# API handler for approval
@app.post("/approvals/{approval_id}/approve")
async def approve(approval_id: str, feedback: ApprovalFeedback):
    approval = db.approvals.get(approval_id)

    # Update approval
    db.approvals.update(approval_id, {
        "status": "approved",
        "feedback": feedback.feedback,
        "reviewed_at": datetime.now()
    })

    # Trigger next workflow
    next_workflow_input = {
        **approval.next_workflow_input,
        "feedback": feedback.feedback
    }

    next_workflow_id = await run_workflow(
        approval.next_workflow_type,
        next_workflow_input
    )

    return {"next_workflow_id": next_workflow_id}
```

**6. Apply feedback workflow runs:**
```python
async def apply_feedback_workflow(input: dict):
    # Load original draft
    draft = db.drafts.get(input["draft_id"])
    feedback = input["feedback"]

    # Apply revisions
    revised = await generate_text(
        model=model,
        prompt=f"Revise this draft based on feedback:\n\nDraft:\n{draft}\n\nFeedback:\n{feedback}"
    )

    # Re-evaluate
    quality_score = await evaluate_quality(revised)

    # Save final version
    db.drafts.update(draft_id, {
        "final_text": revised,
        "final_quality_score": quality_score,
        "status": "finalized"
    })

    return {"final_draft_id": draft_id}
```

---

## How This Works for Different Use Cases

### Use Case 1: Experiment Approval

**Workflow 1: Run Taguchi Experiment**
```python
async def run_taguchi_experiment(config: ExperimentConfig):
    # Run all 8 experiments
    results = []
    for test_config in taguchi_array:
        result = await run_single_test(test_config)
        results.append(result)

    # Analyze main effects
    analysis = analyze_main_effects(results)
    optimal_config = identify_optimal(analysis)

    # Save results and create approval
    experiment_id = db.experiments.create({
        "config": config,
        "results": results,
        "optimal_config": optimal_config,
        "status": "completed"
    })

    # Human needs to review before deploying
    approval_id = db.approvals.create({
        "artifact_type": "experiment_results",
        "artifact_data": {
            "experiment_id": experiment_id,
            "optimal_config": optimal_config,
            "main_effects": analysis,
            "summary": generate_summary(analysis)
        },
        "next_workflow_type": "deploy_config",
        "next_workflow_input": {
            "experiment_id": experiment_id
        }
    })

    return {"experiment_id": experiment_id, "approval_id": approval_id}
```

**Human Reviews:**
- Looks at experiment results
- Validates optimal config makes sense
- Checks quality/cost trade-offs
- Approves or rejects

**Workflow 2: Deploy Optimal Config**
```python
async def deploy_config_workflow(input: dict):
    experiment = db.experiments.get(input["experiment_id"])

    # Deploy optimal config to production
    deploy_workflow_config(
        workflow_name="scene_draft",
        config=experiment.optimal_config,
        environment="production"
    )

    # Update experiment status
    db.experiments.update(experiment_id, {
        "status": "deployed",
        "deployed_at": datetime.now()
    })

    return {"deployed": True}
```

---

### Use Case 2: Draft Review & Revision

**Workflow 1: Generate Draft**
```python
async def generate_draft_workflow(scene_id: str):
    scene = db.scenes.get(scene_id)

    # Generate draft
    draft = await scene_draft_service.generate(scene)

    # Evaluate quality
    quality = await quality_service.evaluate(draft)

    # Save for review
    draft_id = db.drafts.create({
        "scene_id": scene_id,
        "text": draft,
        "quality_score": quality.final_score,
        "status": "pending_review"
    })

    # Create approval
    approval_id = db.approvals.create({
        "artifact_type": "draft",
        "artifact_data": {
            "draft_id": draft_id,
            "text": draft,
            "quality_breakdown": quality.dimensions
        },
        "next_workflow_type": "apply_revision",
        "next_workflow_input": {"draft_id": draft_id}
    })

    return {"draft_id": draft_id}
```

**Workflow 2: Apply Revision** (if human provides feedback)
```python
async def apply_revision_workflow(input: dict):
    draft = db.drafts.get(input["draft_id"])
    feedback = input["feedback"]

    # Apply revision
    revised = await scene_draft_service.revise(draft.text, feedback)

    # Re-evaluate
    quality = await quality_service.evaluate(revised)

    # Update draft
    db.drafts.update(draft_id, {
        "text": revised,
        "quality_score": quality.final_score,
        "revision_count": draft.revision_count + 1,
        "status": "revised"
    })

    # If quality improved significantly, mark as final
    if quality.final_score > draft.quality_score + 10:
        db.drafts.update(draft_id, {"status": "final"})
    else:
        # Create new approval for another round
        create_approval_for_review(draft_id)

    return {"draft_id": draft_id, "quality_improved": True}
```

---

## Process Management: Simplified Options

### Option 1: Synchronous (Simplest)

**No queue at all - workflows run in request/response:**

```python
@app.post("/workflows/generate-draft")
async def generate_draft(request: DraftRequest):
    # Run workflow synchronously
    result = await generate_draft_workflow(request.scene_id)
    return result

# Pros: Dead simple
# Cons: Slow requests (30-60 seconds)
# Good for: MVP, low volume
```

---

### Option 2: Simple Task Queue (Celery/RQ)

**Background processing, simple queue:**

```python
from celery import Celery

app = Celery('llm_optimizer', broker='redis://localhost')

@app.task
def run_workflow(workflow_type: str, input: dict):
    """Execute workflow in background."""
    if workflow_type == "generate_draft":
        result = generate_draft_workflow(input)
    elif workflow_type == "apply_feedback":
        result = apply_feedback_workflow(input)

    return result

# API handler
@app.post("/workflows/generate-draft")
async def generate_draft(request: DraftRequest):
    # Enqueue task
    task = run_workflow.delay("generate_draft", request.dict())

    return {
        "workflow_id": task.id,
        "status": "queued"
    }

# Pros: Fast response, reliable
# Cons: Need Redis/RabbitMQ
# Good for: Production, high volume
```

---

### Option 3: Database Polling (No Queue)

**Ultra-simple, no Redis needed:**

```python
# Cron job / background worker
async def process_pending_workflows():
    """Run every 10 seconds, process pending workflows."""

    pending = db.workflows.find({
        "status": "pending",
        "created_at": {"$lt": datetime.now()}
    }).limit(10)

    for workflow in pending:
        # Mark as running
        db.workflows.update(workflow.id, {"status": "running"})

        # Execute
        try:
            result = await run_workflow(workflow.type, workflow.input)
            db.workflows.update(workflow.id, {
                "status": "completed",
                "output": result
            })
        except Exception as e:
            db.workflows.update(workflow.id, {
                "status": "failed",
                "error": str(e)
            })

# Pros: No queue infrastructure
# Cons: Polling overhead, less scalable
# Good for: MVP, prototyping
```

---

## What We DON'T Need Anymore

### ❌ Temporal
- **Old reason:** Pause/resume workflows
- **New reality:** Workflows complete fast, human reviews between

### ❌ Complex Checkpointing
- **Old reason:** Save workflow state mid-execution
- **New reality:** Just save final output to database

### ❌ Signal/Event System
- **Old reason:** Resume workflows after human input
- **New reality:** Trigger new workflow after approval

### ❌ Long-Running Processes
- **Old reason:** Workflow waits for human
- **New reality:** Workflow completes, human reviews async

---

## What We DO Need

### ✅ Database (PostgreSQL/SQLite)
- Store workflow results
- Track approval queue
- Store human feedback

### ✅ Simple API (FastAPI/Flask)
- Start workflows
- List pending approvals
- Submit approvals (triggers next workflow)

### ✅ Optional: Task Queue (Celery/RQ)
- Background processing
- Retry logic
- Rate limiting

### ✅ Approval UI (Simple)
- List pending reviews
- Show artifact (draft, config, results)
- Collect feedback
- Trigger next workflow

---

## Updated Architecture Diagram

```
┌─────────────────────────────────────────────────┐
│         LLM Workflow Optimizer                  │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │  Workflow Library (Python)               │  │
│  │  - BaseWorkflowService                   │  │
│  │  - TaguchiExperiment                     │  │
│  │  - RubricBasedEvaluator                  │  │
│  │  - Verbalized Sampling                   │  │
│  │                                          │  │
│  │  Each workflow is SIMPLE, SYNCHRONOUS    │  │
│  │  Completes in 10-60 seconds              │  │
│  └──────────────────────────────────────────┘  │
│                       ↕                          │
│  ┌──────────────────────────────────────────┐  │
│  │  API Layer (FastAPI)                     │  │
│  │  - POST /workflows/{type}/run            │  │
│  │  - GET /approvals/pending                │  │
│  │  - POST /approvals/{id}/approve          │  │
│  └──────────────────────────────────────────┘  │
│                       ↕                          │
│  ┌──────────────────────────────────────────┐  │
│  │  Database (PostgreSQL)                   │  │
│  │  - workflows (results)                   │  │
│  │  - approvals (pending queue)             │  │
│  │  - artifacts (drafts, configs)           │  │
│  └──────────────────────────────────────────┘  │
│                       ↕                          │
│  ┌──────────────────────────────────────────┐  │
│  │  Approval UI (Flask/Next.js)             │  │
│  │  - List pending reviews                  │  │
│  │  - Show artifact details                 │  │
│  │  - Collect feedback                      │  │
│  │  - Approve/reject                        │  │
│  └──────────────────────────────────────────┘  │
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │  OPTIONAL: Task Queue (Celery/RQ)        │  │
│  │  - Background workflow execution         │  │
│  │  - Retry logic                           │  │
│  └──────────────────────────────────────────┘  │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Total complexity:** ~5 components (vs 15+ with Temporal)

---

## Implementation Plan (Revised)

### Week 1-2: Core Workflows (Python)

```python
# workflows/
├── __init__.py
├── base.py              # BaseWorkflow abstract class
├── generate_draft.py    # Workflow 1: Generate draft
├── apply_feedback.py    # Workflow 2: Apply revisions
├── run_experiment.py    # Workflow 1: Run Taguchi
└── deploy_config.py     # Workflow 2: Deploy optimal config
```

**Each workflow is simple:**
```python
class BaseWorkflow(ABC):
    @abstractmethod
    async def execute(self, input: dict) -> dict:
        """Execute workflow, return results."""
        pass

    async def run(self, workflow_id: str, input: dict):
        """Wrapper that saves results to database."""
        # Update status
        db.workflows.update(workflow_id, {"status": "running"})

        try:
            # Execute workflow
            result = await self.execute(input)

            # Save result
            db.workflows.update(workflow_id, {
                "status": "completed",
                "output": result,
                "completed_at": datetime.now()
            })

            # Create approval if needed
            if self.requires_approval:
                self.create_approval(workflow_id, result)

            return result

        except Exception as e:
            db.workflows.update(workflow_id, {
                "status": "failed",
                "error": str(e)
            })
            raise
```

---

### Week 3: Database + API

```python
# models/
├── workflow.py
├── approval.py
└── artifact.py

# api/
├── workflows.py    # POST /workflows/{type}/run
├── approvals.py    # GET /approvals/pending, POST /approvals/{id}/approve
└── artifacts.py    # GET /artifacts/{id}
```

**Simple API:**
```python
@app.post("/workflows/{workflow_type}/run")
async def run_workflow(workflow_type: str, input: dict):
    # Create workflow record
    workflow_id = db.workflows.create({
        "type": workflow_type,
        "status": "pending",
        "input": input
    })

    # OPTION A: Run synchronously (simple)
    result = await workflows[workflow_type].run(workflow_id, input)
    return {"workflow_id": workflow_id, "result": result}

    # OPTION B: Enqueue (production)
    task_queue.enqueue(workflows[workflow_type].run, workflow_id, input)
    return {"workflow_id": workflow_id, "status": "queued"}
```

---

### Week 4: Simple Approval UI

```python
# templates/
├── approvals/
│   ├── list.html      # Pending approvals
│   └── review.html    # Review single approval
```

**Minimal UI:**
```html
<!-- approvals/list.html -->
<h1>Pending Approvals</h1>

{% for approval in approvals %}
<div class="approval-card">
  <h3>{{ approval.artifact_type }}</h3>
  <p>Created: {{ approval.created_at }}</p>

  <a href="/approvals/{{ approval.id }}/review">Review</a>
</div>
{% endfor %}

<!-- approvals/review.html -->
<h1>Review {{ approval.artifact_type }}</h1>

<!-- Show the artifact -->
<div class="artifact">
  {{ approval.artifact_data.text }}
</div>

<!-- Quality scores -->
<div class="quality">
  Score: {{ approval.artifact_data.quality_score }}
</div>

<!-- Feedback form -->
<form method="POST" action="/approvals/{{ approval.id }}/approve">
  <textarea name="feedback" placeholder="Your feedback..."></textarea>

  <button name="approved" value="true">Approve</button>
  <button name="approved" value="false">Reject</button>
</form>
```

---

## Benefits of This Approach

### ✅ Simplicity
- Workflows are just async functions
- No complex state machines
- No pause/resume logic
- Easy to test

### ✅ Composability
- Workflows are independent
- Easy to add new workflows
- Human review is external concern
- Framework-agnostic

### ✅ Flexibility
- Can chain workflows any way
- Can skip approval for some workflows
- Can add approval after the fact
- Can batch approve multiple items

### ✅ Debuggability
- Each workflow completes fast
- Clear success/failure
- Easy to re-run
- No "stuck" workflows

### ✅ Scalability
- Workflows are stateless
- Easy to parallelize
- Simple to distribute
- No coordination needed

---

## How This Fits LLM Workflow Optimizer

### Experiment Workflow

**User Journey:**
```
1. User configures experiment (YAML or UI)
   ↓
2. API: POST /workflows/run-experiment
   ↓
3. Workflow: Run Taguchi L8 (8 experiments, ~5-10 min)
   ↓
4. Save results to DB, create approval
   ↓
5. User reviews results in UI
   ↓
6. User approves optimal config
   ↓
7. API: POST /approvals/{id}/approve
   ↓
8. Workflow: Deploy config to production
   ↓
9. Done!
```

**No complex orchestration, no pause/resume, just two simple workflows.**

---

### Scene Drafting Workflow (StoryPunk)

**User Journey:**
```
1. User requests scene draft
   ↓
2. API: POST /workflows/generate-draft
   ↓
3. Workflow: Generate 3 drafts, merge, evaluate (~60 sec)
   ↓
4. Save draft to DB, create approval
   ↓
5. User reviews draft in UI
   ↓
6. User provides revision feedback
   ↓
7. API: POST /approvals/{id}/approve
   ↓
8. Workflow: Apply revisions, re-evaluate (~30 sec)
   ↓
9. Draft finalized!
```

**Two workflows (generate → review → revise), human review in between.**

---

## Recommendation

**This is MUCH better than Temporal/complex orchestration:**

1. ✅ **Simpler to build** - Just workflows + database + simple API
2. ✅ **Easier to understand** - No complex state machines
3. ✅ **More flexible** - Workflows are composable building blocks
4. ✅ **Better for framework** - Users define workflow boundaries
5. ✅ **Production-ready** - Add Celery queue when needed

**Tech Stack:**
- **Core:** Python + LangGraph (simple workflows)
- **Database:** PostgreSQL (workflows, approvals, artifacts)
- **API:** FastAPI (REST endpoints)
- **Queue:** Celery + Redis (optional, add later)
- **UI:** Flask templates (MVP) → Next.js (polish)

**No Temporal, no complex checkpointing, no signals.**

---

## Next Steps

### Prototype This Week

**Day 1-2:** Build two simple workflows
```python
# workflows/example.py

class GenerateDraftWorkflow(BaseWorkflow):
    requires_approval = True
    next_workflow_type = "apply_feedback"

    async def execute(self, input):
        draft = await generate(...)
        quality = await evaluate(...)
        return {"draft": draft, "quality": quality}

class ApplyFeedbackWorkflow(BaseWorkflow):
    requires_approval = False

    async def execute(self, input):
        revised = await revise(input["draft"], input["feedback"])
        return {"final": revised}
```

**Day 3-4:** Build approval queue
```python
# Database models + API endpoints
# Simple Flask UI for review
```

**Day 5:** Test end-to-end
```bash
# Start draft generation
curl -X POST /workflows/generate-draft -d '{"scene_id": "s01"}'
→ {"workflow_id": "wf-123", "approval_id": "app-456"}

# List pending approvals
curl /approvals/pending
→ [{"id": "app-456", "artifact": {...}}]

# Approve with feedback
curl -X POST /approvals/app-456/approve -d '{"feedback": "..."}'
→ {"next_workflow_id": "wf-789"}

# Check final result
curl /workflows/wf-789
→ {"status": "completed", "output": {...}}
```

Want me to prototype this architecture this week?
