import asyncio
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.models.report import ReportPackage
from sqlalchemy import select
from app.db.models.execution import ExecutionPlan

async def seed_reports():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as session:
        # Get an execution plan
        stmt = select(ExecutionPlan).limit(1)
        res = await session.execute(stmt)
        plan = res.scalars().first()
        
        if not plan:
            print("No execution plan found, cannot insert reports.")
            return

        now = datetime.now(timezone.utc)
        reports = [
            ReportPackage(
                execution_id=plan.id,
                title="Coastal Weather & Safety Analysis",
                package_type="MARINE_INTELLIGENCE_REPORT",
                status="COMPLETED"
            ),
            ReportPackage(
                execution_id=plan.id,
                title="PFZ & Vessel Density Report",
                package_type="MARINE_INTELLIGENCE_REPORT",
                status="COMPLETED"
            )
        ]
        session.add_all(reports)
        await session.commit()
        print("Successfully inserted reports.")

if __name__ == "__main__":
    asyncio.run(seed_reports())
