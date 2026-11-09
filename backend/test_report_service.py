import asyncio
from app.db.session import AsyncSessionLocal
from app.services.intelligence.report import ReportService

async def main():
    async with AsyncSessionLocal() as db:
        service = ReportService(db)
        try:
            package_id = await service.create_report_package(
                execution_id="1b885951-aead-4acd-bb31-1ad0ac6588ca",
                title="Cyclone and Coastal Exposure Assessment",
                package_type="MARINE_INTELLIGENCE_REPORT"
            )
            print("Package ID:", package_id)
        except Exception as e:
            print("ERROR:", e)
            import traceback
            traceback.print_exc()

asyncio.run(main())
