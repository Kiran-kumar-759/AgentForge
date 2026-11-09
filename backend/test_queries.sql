-- GeoJSON Test
SELECT 'geojson_marine', ST_AsGeoJSON(geom) FROM marine_observations LIMIT 1;
SELECT 'geojson_cyclone', ST_AsGeoJSON(geom) FROM cyclone_track_points LIMIT 1;
SELECT 'geojson_vessel', ST_AsGeoJSON(geom) FROM vessel_positions LIMIT 1;

-- A. Bounding Box Query (Indian Ocean)
EXPLAIN ANALYZE
SELECT COUNT(*) FROM marine_observations
WHERE geom && ST_MakeEnvelope(60, -10, 100, 30, 4326);

-- B. Distance Query (Distance in meters using geography)
EXPLAIN ANALYZE
SELECT COUNT(*) FROM marine_observations
WHERE ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(74.5, 14.0), 4326)::geography, 50000);

-- C. Nearest Observations
EXPLAIN ANALYZE
SELECT id, ST_Distance(geom, ST_SetSRID(ST_MakePoint(74.5, 14.0), 4326)) as dist
FROM marine_observations
ORDER BY geom <-> ST_SetSRID(ST_MakePoint(74.5, 14.0), 4326)
LIMIT 5;

-- D. Cyclone Track Spatial Query (Indian coastal bounding box)
EXPLAIN ANALYZE
SELECT COUNT(*) FROM cyclone_track_points
WHERE geom && ST_MakeEnvelope(65, 5, 90, 25, 4326);

-- E. Vessel spatial query (Baltic bounding box)
EXPLAIN ANALYZE
SELECT COUNT(*) FROM vessel_positions
WHERE geom && ST_MakeEnvelope(10, 54, 30, 66, 4326);
