import asyncio
import httpx

async def main():
    async with httpx.AsyncClient() as client:
        res = await client.post("http://localhost:8000/api/v1/reports", json={"execution_id":"1b885951-aead-4acd-bb31-1ad0ac6588ca","title":"Cyclone and Coastal Exposure Assessment","package_type":"MARINE_INTELLIGENCE_REPORT"})
        print(res.status_code)
        print(res.text)

asyncio.run(main())
