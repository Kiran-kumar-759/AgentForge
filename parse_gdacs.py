import requests
import json
res = requests.get("https://www.gdacs.org/gdacsapi/api/polygons/getgeometry?eventtype=TC&eventid=1001331&episodeid=10")
data = res.json()
for feature in data.get("features", []):
    if feature.get("properties", {}).get("Class", "").startswith("Point_Polygon_Point"):
        label = feature["properties"].get("polygonlabel")
        print(f"Label: {label}")
