# ORCA — PHASE 12 COMPLETION REPORT
## Long-Running Jobs & Replanning

### 1. Objective Status
The core objective of Phase 12 has been **successfully achieved**. ORCA's execution architecture has been fully upgraded from synchronous, blocking requests to a robust asynchronous framework capable of managing long-running tasks, retries, and intelligent replanning. 

The `AgentOrchestrator` execution flows are now entirely detached from the HTTP cycle, running securely as background jobs on the Celery/Valkey infrastructure, while preserving strict Phase 11 graph compliance.

### 2. Implementation Summary

- **Asynchronous Execution (Celery Integration)**:
  - Disconnected `AgentOrchestrator.execute_query` from synchronous LangGraph invocation.
  - Implemented `AgentOrchestrator.create_plan` in the foreground to persist the `ExecutionPlan` intent and steps instantly.
  - Created a robust Celery task worker (`agent.execution.run` in `app/workers/tasks/execution.py`) that executes `AgentOrchestrator.run_execution` asynchronously.

- **Frontend State Tracking Integration**:
  - The API endpoint `GET /executions/{execution_id}` was updated to seamlessly handle parent-child plan transitions.
  - The React frontend `AgentConsole` was extended to visually present `RETRYING` capabilities seamlessly, reflecting accurate `ExecutionNode` states within the ReactFlow DAG diagram dynamically as background tasks progress.

- **Bounded Retry Mechanism**:
  - Added deterministic bounded retries (up to 2 attempts) directly inside `AgentOrchestrator._execute_capability`.
  - Temporary provider failures intelligently trigger `NODE_RETRY_STARTED` events.
  - Missing geographic coverages (`CAPABILITY_UNAVAILABLE`) are classified as immediate terminal failures to prevent pointless retries.

- **Intelligent Replanning**:
  - Integrated a `generate_replan` workflow in the `PlannerService` that operates upon terminal node failure detection (after retries exhaust).
  - The orchestrator dynamically builds a child `ExecutionPlan` pointing to its `parent_plan_id`.
  - Re-evaluates capabilities logically by stripping out failed paths while securely reviving and persisting completely finished capabilities via `NODE_REUSED` events, drastically saving compute and avoiding duplicate API calls.

### 3. Verification Criteria Checklist
- [x] **No Sync Blocking**: `POST /chat` returns instantly with `status="running"` while the heavy lifting proceeds on Celery.
- [x] **No Docker Needed**: Zero new orchestration engine dependencies introduced. Native Celery framework gracefully utilized.
- [x] **Reused States**: Nodes completed successfully before a terminal failure do not needlessly repeat in the replanned child graph.
- [x] **Data Integrity Assured**: `AgentOrchestrator` never hallucinates synthetic outputs upon external provider failure.
- [x] **Strict Roadmap Adherence**: Only Phase 12 goals were executed.

### 4. Next Steps Prepared
ORCA is now fully capable of asynchronously executing multi-step analytic tasks without locking up the user interface. It detects systemic failures intelligently and corrects course when possible. 

The system architecture is primed and ready to begin **Phase 13 — Evidence & Verification**, which will introduce the `Evidence Graph` layer validating output credibility and providing verifiable sourcing to users.
