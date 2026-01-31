import logging
import duckdb

class DatabaseHandler:
    def __init__(self, db_path):
        self.connection = duckdb.connect(db_path)
        self.cursor = self.connection.cursor()
        logging.info(f"Connected to DuckDB: {db_path}.")

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

        # trip_updates table
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
            SELECT
                vehicle_id,
                route_id,
                timestamp,
                lat,
                lon,
                LAG(lat) OVER (PARTITION BY vehicle_id ORDER BY timestamp) as prev_lat,
                LAG(lon) OVER (PARTITION BY vehicle_id ORDER BY timestamp) as prev_lon,
                LAG(timestamp) OVER (PARTITION BY vehicle_id ORDER BY timestamp) as prev_time
            FROM vehicle_positions
        """)

        self.connection.execute("""
            CREATE OR REPLACE VIEW view_tram_headway AS
            SELECT
                route_id,
                stop_id,
                trip_id,
                arrival_time,
                LAG(arrival_time) OVER (PARTITION BY stop_id ORDER BY arrival_time) as prev_arrival_time,
                (arrival_time - LAG(arrival_time) OVER (PARTITION BY stop_id ORDER BY arrival_time)) / 60.0 as headway_min
            FROM trip_updates
            WHERE stop_id IS NOT NULL
        """)

    def save_vehicle(self, timestamp, route_id, vid, lat, lon):
        self.connection.execute(
            "INSERT INTO vehicle_positions VALUES (?, ?, ?, ?, ?)",
            [timestamp, str(route_id), str(vid), lat, lon]
        )

    def save_trip_update(self, timestamp, trip_id, route_id, stop_id, stop_sequence, 
                        arrival_delay, arrival_time, 
                        departure_delay, departure_time):
        
        # We construct the list in the EXACT order of the SQL table columns
        # Table: (timestamp, trip_id, route_id, stop_id, stop_sequence, arr_delay, arr_time, dep_delay, dep_time)
        
        self.connection.execute(
            "INSERT INTO trip_updates VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [timestamp, str(trip_id), str(route_id), str(stop_id), stop_sequence,
            arrival_delay, arrival_time, departure_delay, departure_time]
        )

    def close(self):
        self.connection.close()
        logging.info("DuckDB connection closed.")