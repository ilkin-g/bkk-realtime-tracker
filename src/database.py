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

    def _read_sql(self, filename):
        with open(f"./queries/{filename}", "r") as f:
            return f.read()

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

        self.connection.execute(self._read_sql("view_tram_movement.sql"))
        self.connection.execute(self._read_sql("view_tram_headway.sql"))
        self.connection.execute(self._read_sql("view_schedule_adherence.sql"))

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