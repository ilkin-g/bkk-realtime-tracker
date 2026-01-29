import logging
import sqlite3

class DatabaseHandler:
    def __init__(self, file_name):
        self.connection = sqlite3.connect(file_name)
        self.cursor = self.connection.cursor()
        logging.info(f"Connected to SQLite database: {file_name}.")

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS vehicle_positions (
                timestamp INTEGER,
                route_id TEXT,
                vehicle_id TEXT,
                lat REAL,
                lon REAL
            )'''
        )

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS trip_updates (
                timestamp INTEGER,
                trip_id TEXT,
                route_id TEXT,
                stop_id TEXT,
                stop_sequence INT,
                arrival_delay INT,
                arrival_time INT,
                departure_delay INT,
                departure_time INT
            )'''
        )
        self.connection.commit()

    def __insert_rows(self, table, *args):
        placeholders = ', '.join(['?'] * len(args))
        sql = f'INSERT INTO {table} VALUES ({placeholders})'
        
        try:
            self.cursor.execute(sql, args)
            self.connection.commit()
        except sqlite3.Error as e:
            logging.error(f"Database error: {e}")

    def save_vehicle(self, timestamp, route_id, vid, lat, lon):
        self.__insert_rows("vehicle_positions", timestamp, route_id, vid, lat, lon)

    def save_trip_update(self, timestamp, trip_id, route_id, stop_id, stop_sequence, arrival_delay, arrival_time, departure_delay, departure_time):
        self.__insert_rows("trip_updates", timestamp, trip_id, route_id, stop_id, stop_sequence, arrival_delay, arrival_time, 
                    departure_delay, departure_time)

    def close(self):
        self.connection.close()
        logging.info("Database connection closed.")