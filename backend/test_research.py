import asyncio
import httpx
import json

async def test_research():
    payload = {
        "question": "Analyze marine conditions near Goa over the next 72 hours and their effect on coastal infrastructure.",
        "workspace_id": "WS_TEST",
        "geographic_scope": {
            "type": "bbox",
            "coordinates": [73.5, 15.0, 74.5, 16.0]
        },
        "mode": "deep"
    }
    
    print("Submitting research request...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post("http://localhost:8000/api/v1/research/", json=payload)
        
        print("Status Code:", resp.status_code)
        
        try:
            data = resp.json()
            print("Response:", json.dumps(data, indent=2))
        except Exception as e:
            print("Failed to decode JSON:", resp.text)

if __name__ == "__main__":
    asyncio.run(test_research())
