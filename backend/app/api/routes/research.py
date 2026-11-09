from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.db.session import get_db
from app.db.models.research import ResearchRequest
from app.services.intelligence.research_engine import ResearchEngine
from pydantic import BaseModel

router = APIRouter()

class ResearchRequestPayload(BaseModel):
    question: str
    workspace_id: str
    geographic_scope: Optional[Dict[str, Any]] = None
    temporal_scope: Optional[Dict[str, Any]] = None
    mode: str = "quick"

@router.post("/", response_model=Dict[str, Any])
async def create_research(payload: ResearchRequestPayload, db: AsyncSession = Depends(get_db)):
    req = ResearchRequest(
        question=payload.question,
        workspace_id=payload.workspace_id,
        geographic_scope=payload.geographic_scope,
        temporal_scope=payload.temporal_scope,
        mode=payload.mode
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    
    # Normally this would be enqueued to Celery. 
    # For Phase 9 deterministic sync execution, we run it directly.
    engine = ResearchEngine(db)
    result_req = await engine.execute_research(req.id)
    
    return {
        "research_id": str(result_req.id),
        "status": result_req.status,
        "executive_summary": result_req.executive_summary,
        "findings": result_req.findings,
        "limitations": result_req.limitations,
        "created_at": result_req.created_at.isoformat() if result_req.created_at else None,
        "completed_at": result_req.completed_at.isoformat() if result_req.completed_at else None
    }

@router.get("/{request_id}", response_model=Dict[str, Any])
async def get_research(request_id: str, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    stmt = select(ResearchRequest).where(ResearchRequest.id == uuid.UUID(request_id))
    res = await db.execute(stmt)
    req = res.scalars().first()
    
    if not req:
        raise HTTPException(status_code=404, detail="Research request not found")
        
    return {
        "research_id": str(req.id),
        "status": req.status,
        "executive_summary": req.executive_summary,
        "findings": req.findings,
        "limitations": req.limitations,
        "created_at": req.created_at.isoformat() if req.created_at else None,
        "completed_at": req.completed_at.isoformat() if req.completed_at else None
    }
