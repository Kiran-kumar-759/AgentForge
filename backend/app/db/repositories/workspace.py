from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.workspace import Workspace
from app.schemas.workspace import WorkspaceCreate

class WorkspaceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self) -> List[Workspace]:
        result = await self.session.execute(select(Workspace))
        return list(result.scalars().all())

    async def get_by_code(self, code: str) -> Workspace | None:
        result = await self.session.execute(
            select(Workspace).where(Workspace.code == code)
        )
        return result.scalars().first()

    async def create(self, workspace_in: WorkspaceCreate) -> Workspace:
        workspace = Workspace(**workspace_in.model_dump())
        self.session.add(workspace)
        await self.session.commit()
        await self.session.refresh(workspace)
        return workspace
