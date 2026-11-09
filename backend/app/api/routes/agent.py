import uuid
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.db.models.execution import ExecutionPlan, ExecutionNode, ExecutionEdge
from app.services.intelligence.orchestrator import AgentOrchestrator

router = APIRouter(prefix="/agent", tags=["agent"])

class ChatRequest(BaseModel):
    conversation_id: Optional[uuid.UUID] = None
    workspace_code: str
    message: str
    context: Optional[Dict[str, Any]] = None

@router.post("/chat")
async def agent_chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    orchestrator = AgentOrchestrator(db)
    
    code_map = {
        "command-center": "COMMAND_CENTER",
        "fisherman": "FISHERMAN",
        "researcher": "RESEARCHER",
        "coastal-authority": "COASTAL_AUTHORITY",
        "disaster-management": "DISASTER_MANAGEMENT",
        "maritime-operator": "MARITIME_OPERATOR"
    }
    db_code = code_map.get(req.workspace_code, req.workspace_code)
    
    try:
        result = await orchestrator.execute_query(
            query=req.message,
            workspace_code=db_code,
            context_data=req.context,
            conversation_id=str(req.conversation_id) if req.conversation_id else None
        )
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/executions/{execution_id}")
async def get_execution_status(execution_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(ExecutionPlan)
        .where(ExecutionPlan.id == execution_id)
        .options(selectinload(ExecutionPlan.nodes), selectinload(ExecutionPlan.edges))
    )
    res = await db.execute(stmt)
    plan = res.scalars().first()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Execution not found")
    while True:
        child_stmt = select(ExecutionPlan).where(ExecutionPlan.parent_plan_id == plan.id).options(selectinload(ExecutionPlan.nodes), selectinload(ExecutionPlan.edges))
        child_res = await db.execute(child_stmt)
        child_plan = child_res.scalars().first()
        if child_plan:
            plan = child_plan
        else:
            break
    return {
        "execution_id": str(plan.id),
        "conversation_id": str(plan.conversation_id),
        "status": plan.status,
        "intent": plan.intent_type,
        "started_at": plan.started_at,
        "completed_at": plan.completed_at,
        "nodes": [
            {
                "id": str(n.id),
                "node_id": n.node_id,
                "agent_code": n.agent_code,
                "capability_code": n.capability_code,
                "node_type": n.node_type,
                "status": n.status,
                "started_at": n.started_at,
                "completed_at": n.completed_at,
                "duration_ms": n.duration_ms,
                "output": n.output_data,
                "error": n.error
            } for n in plan.nodes
        ],
        "edges": [
            {
                "source": e.source_node_id,
                "target": e.target_node_id,
                "type": e.edge_type
            } for e in plan.edges
        ]
    }

@router.get("/executions/{execution_id}/events")
async def get_execution_events(execution_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    from app.db.models.execution import ExecutionEvent
    stmt = (
        select(ExecutionEvent)
        .where(ExecutionEvent.execution_plan_id == execution_id)
        .order_by(ExecutionEvent.sequence_number.asc(), ExecutionEvent.timestamp.asc())
    )
    res = await db.execute(stmt)
    events = res.scalars().all()
    
    return [
        {
            "id": str(e.id),
            "execution_plan_id": str(e.execution_plan_id),
            "execution_node_id": str(e.execution_node_id) if e.execution_node_id else None,
            "event_type": e.event_type,
            "agent_id": e.agent_id,
            "capability_id": e.capability_id,
            "status": e.status,
            "message": e.message,
            "payload": e.payload,
            "timestamp": e.timestamp
        } for e in events
    ]

@router.get("/executions/{execution_id}/evidence")
async def get_execution_evidence(execution_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    from app.db.models.evidence import Claim, Evidence
    
    # First get the correct child plan if replanned
    stmt = select(ExecutionPlan).where(ExecutionPlan.id == execution_id)
    res = await db.execute(stmt)
    plan = res.scalars().first()
    if not plan:
        raise HTTPException(status_code=404, detail="Execution not found")
        
    while True:
        child_stmt = select(ExecutionPlan).where(ExecutionPlan.parent_plan_id == plan.id)
        child_res = await db.execute(child_stmt)
        child_plan = child_res.scalars().first()
        if child_plan:
            plan = child_plan
        else:
            break
            
    # Get claims for this plan
    stmt = (
        select(Claim)
        .where(Claim.execution_id == plan.id)
        .options(selectinload(Claim.evidence))
    )
    res = await db.execute(stmt)
    claims = res.scalars().all()
    
    # Extract evidence deduplicated
    evidence_map = {}
    for c in claims:
        for e in c.evidence:
            if e.id not in evidence_map:
                evidence_map[e.id] = e
                
    # Also fetch evidence attached to the execution_id that might not be on a claim
    stmt = select(Evidence).where(Evidence.execution_id == plan.id)
    res = await db.execute(stmt)
    all_evidence = res.scalars().all()
    for e in all_evidence:
        if e.id not in evidence_map:
            evidence_map[e.id] = e
            
    return {
        "execution_id": str(plan.id),
        "claims": [
            {
                "id": str(c.id),
                "execution_node_id": str(c.execution_node_id) if c.execution_node_id else None,
                "text": c.claim_text,
                "type": c.claim_type,
                "verification_status": c.verification_status,
                "reason": c.verification_reason,
                "evidence_ids": [str(e.id) for e in c.evidence],
                "metadata": c.metadata_
            } for c in claims
        ],
        "evidence": [
            {
                "id": str(e.id),
                "execution_node_id": str(e.execution_node_id) if e.execution_node_id else None,
                "type": e.evidence_type,
                "dataset_id": e.dataset_id,
                "source_name": e.source_name,
                "source_url": e.source_url,
                "retrieved_at": e.retrieved_at.isoformat() if e.retrieved_at else None,
                "observation_time": e.observation_time.isoformat() if e.observation_time else None,
                "summary": e.summary,
                "status": e.status
            } for e in evidence_map.values()
        ]
    }

@router.get("/evidence")
async def list_workspace_evidence(workspace: str, limit: int = 20, db: AsyncSession = Depends(get_db)):
    from app.db.models.evidence import Claim, Evidence
    
    code_map = {
        "command-center": "COMMAND_CENTER",
        "fisherman": "FISHERMAN",
        "researcher": "RESEARCHER",
        "coastal-authority": "COASTAL_AUTHORITY",
        "disaster-management": "DISASTER_MANAGEMENT",
        "maritime-operator": "MARITIME_OPERATOR"
    }
    db_code = code_map.get(workspace, workspace)
    
    stmt = (
        select(ExecutionPlan)
        .where(ExecutionPlan.workspace_code == db_code)
        .order_by(ExecutionPlan.started_at.desc())
        .limit(limit)
    )
    res = await db.execute(stmt)
    plans = res.scalars().all()
    
    plan_ids = [p.id for p in plans]
    
    if not plan_ids:
        return {"claims": [], "evidence": []}
        
    stmt = select(Claim).where(Claim.execution_id.in_(plan_ids)).options(selectinload(Claim.evidence))
    res = await db.execute(stmt)
    claims = res.scalars().all()
    
    evidence_map = {}
    for c in claims:
        for e in c.evidence:
            if e.id not in evidence_map:
                evidence_map[e.id] = e
                
    stmt = select(Evidence).where(Evidence.execution_id.in_(plan_ids))
    res = await db.execute(stmt)
    all_evidence = res.scalars().all()
    for e in all_evidence:
        if e.id not in evidence_map:
            evidence_map[e.id] = e
            
    return {
        "claims": [
            {
                "id": str(c.id),
                "execution_id": str(c.execution_id),
                "text": c.claim_text,
                "type": c.claim_type,
                "verification_status": c.verification_status,
                "evidence_ids": [str(e.id) for e in c.evidence]
            } for c in claims
        ],
        "evidence": [
            {
                "id": str(e.id),
                "type": e.evidence_type,
                "provider": e.source_name,
                "observation_time": e.observation_time.isoformat() if e.observation_time else None
            } for e in evidence_map.values()
        ]
    }

