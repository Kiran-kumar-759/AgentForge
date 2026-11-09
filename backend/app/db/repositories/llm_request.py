from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.llm import LLMRequest

class LLMRequestRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, **kwargs) -> LLMRequest:
        req = LLMRequest(**kwargs)
        self.session.add(req)
        await self.session.commit()
        await self.session.refresh(req)
        return req
