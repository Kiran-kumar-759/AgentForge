SELECT 
    'marine_observations' as table_name,
    COUNT(*) as total_rows,
    COUNT(*) FILTER (WHERE latitude IS NULL OR longitude IS NULL) as null_coords,
    COUNT(*) FILTER (WHERE latitude < -90 OR latitude > 90 OR longitude < -180 OR longitude > 180) as invalid_coords,
    MIN(latitude) as min_lat,
    MAX(latitude) as max_lat,
    MIN(longitude) as min_lon,
    MAX(longitude) as max_lon
FROM marine_observations
UNION ALL
SELECT 
    'cyclone_track_points' as table_name,
    COUNT(*) as total_rows,
    COUNT(*) FILTER (WHERE latitude IS NULL OR longitude IS NULL) as null_coords,
    COUNT(*) FILTER (WHERE latitude < -90 OR latitude > 90 OR longitude < -180 OR longitude > 180) as invalid_coords,
    MIN(latitude) as min_lat,
    MAX(latitude) as max_lat,
    MIN(longitude) as min_lon,
    MAX(longitude) as max_lon
FROM cyclone_track_points
UNION ALL
SELECT 
    'vessel_positions' as table_name,
    COUNT(*) as total_rows,
    COUNT(*) FILTER (WHERE latitude IS NULL OR longitude IS NULL) as null_coords,
    COUNT(*) FILTER (WHERE latitude < -90 OR latitude > 90 OR longitude < -180 OR longitude > 180) as invalid_coords,
    MIN(latitude) as min_lat,
    MAX(latitude) as max_lat,
    MIN(longitude) as min_lon,
    MAX(longitude) as max_lon
FROM vessel_positions;
