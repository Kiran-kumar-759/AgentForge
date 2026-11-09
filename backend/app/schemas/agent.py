from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from app.db.models.agent import AgentStatus

class AgentBase(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    version: str
    status: AgentStatus
    agent_type: str
    input_schema: Optional[dict] = None
    output_schema: Optional[dict] = None

class AgentCreate(AgentBase):
    pass

class AgentResponse(AgentBase):
    id: UUID
    capabilities: List[str] = []

    class Config:
        from_attributes = True
