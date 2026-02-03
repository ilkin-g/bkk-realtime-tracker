CREATE OR REPLACE VIEW view_tram_movement AS
WITH deduped AS (
    SELECT DISTINCT ON (vehicle_id, timestamp) * FROM vehicle_positions
),
with_lag AS (
    SELECT 
        vehicle_id, route_id, timestamp, lat, lon,
        LAG(lat) OVER (PARTITION BY vehicle_id ORDER BY timestamp) as prev_lat,
        LAG(lon) OVER (PARTITION BY vehicle_id ORDER BY timestamp) as prev_lon,
        LAG(timestamp) OVER (PARTITION BY vehicle_id ORDER BY timestamp) as prev_time
    FROM deduped
)
SELECT 
    *,
    ST_Distance_Spheroid(
        ST_Point(lon, lat), 
        ST_Point(prev_lon, prev_lat)
    ) as dist_meters,
    
    (timestamp - prev_time) as time_diff_sec,
    
    CASE 
        WHEN (timestamp - prev_time) > 0 THEN 
            (ST_Distance_Spheroid(ST_Point(lon, lat), ST_Point(prev_lon, prev_lat)) / (timestamp - prev_time)) * 3.6
        ELSE 0 
    END as speed_kmh
FROM with_lag
WHERE prev_lat IS NOT NULL
AND dist_meters > 5