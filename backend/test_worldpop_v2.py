import httpx
import json

def test_worldpop_v2():
    url = "https://api.worldpop.org/v2/population"
    payload = {
      "geojson": {
        "type": "Polygon",
        "coordinates": [
          [
            [72.8, 18.8],
            [73.2, 18.8],
            [73.2, 19.2],
            [72.8, 19.2],
            [72.8, 18.8]
          ]
        ]
      },
      "year": 2020,
      "resolution": "1km"
    }
    
    print("Testing WorldPop v2...")
    try:
        resp = httpx.post(url, json=payload, timeout=20.0)
        print("Status:", resp.status_code)
        print("Response Body:", resp.text)
        
        if resp.status_code == 200:
            data = resp.json()
            taskid = data.get("taskid")
            if taskid:
                print(f"Got task ID: {taskid}")
                print(f"Polling https://api.worldpop.org/v2/tasks/{taskid} ...")
                # Wait or poll
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test_worldpop_v2()
