import asyncio
from app.workers.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.services.intelligence.report import ReportService

@celery_app.task(name="generate_report_task")
def generate_report_task(package_id: str):
    async def run_generation():
        async with AsyncSessionLocal() as db:
            service = ReportService(db)
            await service.generate_report(package_id)

    asyncio.run(run_generation())
