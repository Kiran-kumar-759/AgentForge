import asyncio
import json
from app.services.exposure.worldpop import WorldPopProvider
import httpx

async def test_worldpop():
    provider = WorldPopProvider()
    geometry = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [73.7, 15.4],
                            [73.8, 15.4],
                            [73.8, 15.5],
                            [73.7, 15.5],
                            [73.7, 15.4]
                        ]
                    ]
                }
            }
        ]
    }
    try:
        res = await provider.get_population(geometry, year=2020)
        print("WORLDPOP INITIAL RESPONSE:")
        print(json.dumps(res, indent=2))
        
        if "task_id" in res or "taskid" in res:
            task_id = res.get("task_id") or res.get("taskid")
            check_url = res.get("check_url", f"https://api.worldpop.org/v1/tasks/{task_id}")
            if check_url.startswith("/"):
                check_url = f"https://api.worldpop.org{check_url}"
                
            print(f"POLLING {check_url}...")
            async with httpx.AsyncClient(timeout=30) as client:
                for i in range(15):
                    await asyncio.sleep(5)
                    poll_resp = await client.get(check_url)
                    poll_resp.raise_for_status()
                    poll_data = poll_resp.json()
                    print(f"POLL {i}: {poll_data.get('status')}")
                    if poll_data.get('status') == 'completed' or poll_data.get('status') == 'finished':
                        print("FINAL RESULT:")
                        print(json.dumps(poll_data, indent=2))
                        break
                    elif poll_data.get('status') == 'error' or poll_data.get('status') == 'failed':
                        print("FAILED:", poll_data)
                        break
    except Exception as e:
        print("ERROR:", e)

if __name__ == "__main__":
    asyncio.run(test_worldpop())
