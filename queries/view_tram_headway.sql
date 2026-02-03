CREATE OR REPLACE VIEW view_tram_headway AS
WITH distinct_arrivals AS (
    SELECT DISTINCT ON (route_id, stop_id, trip_id) 
        route_id, stop_id, trip_id, arrival_time
    FROM trip_updates
    WHERE stop_id IS NOT NULL
    ORDER BY route_id, stop_id, trip_id, timestamp DESC
)
SELECT 
    route_id, stop_id, trip_id, arrival_time,
    LAG(arrival_time) OVER (PARTITION BY stop_id ORDER BY arrival_time) as prev_arrival_time,
    (arrival_time - LAG(arrival_time) OVER (PARTITION BY stop_id ORDER BY arrival_time)) / 60.0 as headway_min
FROM distinct_arrivals