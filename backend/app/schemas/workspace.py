from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
import uuid

class WorkspaceBase(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    is_active: bool = True

class WorkspaceCreate(WorkspaceBase):
    pass

class WorkspaceResponse(WorkspaceBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
