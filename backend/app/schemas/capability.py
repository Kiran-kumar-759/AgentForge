from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from app.db.models.capability import CapabilityCategory, CapabilityStatus

class CapabilityBase(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    category: CapabilityCategory
    version: str
    status: CapabilityStatus
    input_schema: Optional[dict] = None
    output_schema: Optional[dict] = None
    required_data: Optional[dict] = None
    required_parameters: Optional[dict] = None

class CapabilityCreate(CapabilityBase):
    pass

class CapabilityResponse(CapabilityBase):
    id: UUID
    agents: List[str] = []

    class Config:
        from_attributes = True

class WorkspaceCapabilityResponse(BaseModel):
    workspace_code: str
    capability_code: str
    enabled: bool
    capability: CapabilityResponse

    class Config:
        from_attributes = True
