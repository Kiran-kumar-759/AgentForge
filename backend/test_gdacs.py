import asyncio
import httpx
from datetime import datetime, timezone

async def main():
    url = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/MAP?eventtype=TC"
    async with httpx.AsyncClient() as client:
        res = await client.get(url, timeout=30.0)
        data = res.json()
        active = []
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            todate_str = props.get("todate")
            if not todate_str: continue
            try:
                dt = datetime.strptime(todate_str, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
                if (datetime.now(timezone.utc) - dt).days <= 7:
                    active.append(props)
            except Exception:
                pass
        print(f"Found {len(active)} active events in last 7 days.")
        for a in active:
            print(f"Event: {a.get('eventname')} {a.get('eventid')} {a.get('todate')}")

asyncio.run(main())
