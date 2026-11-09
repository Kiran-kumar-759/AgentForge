from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.schemas.workspace import WorkspaceResponse
from app.db.session import get_db
from app.db.repositories.workspace import WorkspaceRepository

router = APIRouter(tags=["workspaces"])

@router.get("", response_model=List[WorkspaceResponse])
async def get_workspaces(db: AsyncSession = Depends(get_db)):
    repo = WorkspaceRepository(db)
    workspaces = await repo.get_all()
    return workspaces
