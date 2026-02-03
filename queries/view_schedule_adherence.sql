CREATE OR REPLACE VIEW view_schedule_adherence AS
WITH latest_updates AS (
    SELECT DISTINCT ON (trip_id, stop_sequence) 
        trip_id, stop_sequence, arrival_time
    FROM trip_updates
    WHERE arrival_time IS NOT NULL
),
parsed_schedule AS (
    SELECT 
        trip_id, stop_sequence, arrival_time as scheduled_string,
        (CAST(SPLIT_PART(arrival_time, ':', 1) AS INTEGER) * 3600 +
            CAST(SPLIT_PART(arrival_time, ':', 2) AS INTEGER) * 60 +
            CAST(SPLIT_PART(arrival_time, ':', 3) AS INTEGER)) as sched_sec_midnight        
    FROM static_schedule
)
SELECT 
    lu.trip_id,
    lu.stop_sequence,
    (
        (date_part('hour', timezone('Europe/Budapest', to_timestamp(lu.arrival_time))) * 3600) +
        (date_part('minute', timezone('Europe/Budapest', to_timestamp(lu.arrival_time))) * 60) +
        (date_part('second', timezone('Europe/Budapest', to_timestamp(lu.arrival_time))))
        - ps.sched_sec_midnight
    ) / 60.0 as delay_minutes,
    
    ps.scheduled_string,
    lu.arrival_time as actual_ts
FROM latest_updates lu
JOIN parsed_schedule ps 
    ON lu.trip_id = ps.trip_id 
    AND lu.stop_sequence = ps.stop_sequence