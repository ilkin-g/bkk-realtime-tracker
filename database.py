import logging
import duckdb

class DatabaseHandler:
    def __init__(self, db_path):
        self.connection = duckdb.connect(db_path)
        self.cursor = self.connection.cursor()
        logging.info(f"Connected to DuckDB: {db_path}.")

        try:
            self.connection.execute("INSTALL spatial; LOAD spatial;")
            self.connection.execute("INSTALL icu; LOAD icu;")
            logging.info("DuckDB Spatial & ICU extensions loaded.")
        except Exception as e:
            logging.error(f"Could not load Spatial extension: {e}")

        self._create_tables()
        self._create_views()

    def _create_tables(self):
        self.connection.execute('''
            CREATE TABLE IF NOT EXISTS vehicle_positions (
                timestamp BIGINT,
                route_id VARCHAR,
                vehicle_id VARCHAR,
                lat DOUBLE,
                lon DOUBLE
            )
        ''')

        self.connection.execute('''
            CREATE TABLE IF NOT EXISTS trip_updates (
                timestamp BIGINT,
                trip_id VARCHAR,
                route_id VARCHAR,
                stop_id VARCHAR,
                stop_sequence INTEGER,
                arrival_delay INTEGER,
                arrival_time BIGINT,
                departure_delay INTEGER,
                departure_time BIGINT
            )
        ''')
        
        self.connection.execute('''
            CREATE TABLE IF NOT EXISTS static_schedule (
                trip_id VARCHAR,
                arrival_time VARCHAR,
                stop_id VARCHAR,
                stop_sequence INTEGER
            )
        ''')

    def _create_views(self):
        logging.info("Creating SQL views for analytics...")

        self.connection.execute("""
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
        """)

        self.connection.execute("""
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
        """)

        self.connection.execute("""
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
                    -- Parse "14:30:00" into seconds from midnight
                    (CAST(SPLIT_PART(arrival_time, ':', 1) AS INTEGER) * 3600 +
                     CAST(SPLIT_PART(arrival_time, ':', 2) AS INTEGER) * 60 +
                     CAST(SPLIT_PART(arrival_time, ':', 3) AS INTEGER)) as sched_sec_midnight        
                FROM static_schedule
            )
            SELECT 
                lu.trip_id,
                lu.stop_sequence,
                -- THE FIX: Dynamic Timezone Conversion
                -- 1. to_timestamp() converts the UTC integer to a UTC timestamp object
                -- 2. timezone('Europe/Budapest', ...) shifts it to local time (handling DST automatically)
                -- 3. We extract the hour/min/sec from that LOCAL time to compare with the schedule
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
        """)

    def save_vehicles_bulk(self, vehicle_list):
        if not vehicle_list:
            return

        self.connection.executemany(
            "INSERT INTO vehicle_positions VALUES (?, ?, ?, ?, ?)",
            vehicle_list
        )

    def save_trip_updates_bulk(self, update_list):
        if not update_list:
            return

        self.connection.executemany(
            "INSERT INTO trip_updates VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            update_list
        )

    def close(self):
        self.connection.close()
        logging.info("DuckDB connection closed.")