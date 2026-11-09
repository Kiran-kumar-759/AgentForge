-- A. Row counts
SELECT 'marine_observations' as table, count(*) from marine_observations UNION ALL
SELECT 'cyclone_events', count(*) from cyclone_events UNION ALL
SELECT 'cyclone_track_points', count(*) from cyclone_track_points UNION ALL
SELECT 'vessels', count(*) from vessels UNION ALL
SELECT 'vessel_positions', count(*) from vessel_positions;

-- B. Geometry count
SELECT 'marine_observations_geom' as metric, count(*) as count, count(geom) as has_geom, count(*) - count(geom) as missing_geom from marine_observations UNION ALL
SELECT 'cyclone_track_points_geom', count(*), count(geom), count(*) - count(geom) from cyclone_track_points UNION ALL
SELECT 'vessel_positions_geom', count(*), count(geom), count(*) - count(geom) from vessel_positions;

-- C. Geometry validity
SELECT 'invalid_marine_geom' as metric, count(*) from marine_observations where ST_IsValid(geom) = false UNION ALL
SELECT 'invalid_cyclone_geom', count(*) from cyclone_track_points where ST_IsValid(geom) = false UNION ALL
SELECT 'invalid_vessel_geom', count(*) from vessel_positions where ST_IsValid(geom) = false;

-- D & E. Geometry type & SRID
SELECT 'marine_geom_type_srid' as metric, GeometryType(geom) as gtype, ST_SRID(geom) as srid from marine_observations where geom is not null limit 1;
SELECT 'cyclone_geom_type_srid' as metric, GeometryType(geom) as gtype, ST_SRID(geom) as srid from cyclone_track_points where geom is not null limit 1;
SELECT 'vessel_geom_type_srid' as metric, GeometryType(geom) as gtype, ST_SRID(geom) as srid from vessel_positions where geom is not null limit 1;

-- F. Coordinate consistency
SELECT 'marine_coord_check' as metric, longitude, ST_X(geom) as st_x, latitude, ST_Y(geom) as st_y from marine_observations where geom is not null limit 1;
SELECT 'cyclone_coord_check' as metric, longitude, ST_X(geom) as st_x, latitude, ST_Y(geom) as st_y from cyclone_track_points where geom is not null limit 1;
SELECT 'vessel_coord_check' as metric, longitude, ST_X(geom) as st_x, latitude, ST_Y(geom) as st_y from vessel_positions where geom is not null limit 1;
