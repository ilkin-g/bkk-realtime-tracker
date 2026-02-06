import unittest
import time
from unittest.mock import MagicMock
from src.database import DatabaseHandler

class TestDatabase(unittest.TestCase):
    def setUp(self):
        # 1. Initialize DB in memory
        DatabaseHandler._read_sql = MagicMock(return_value="SELECT 1;") 
        self.db = DatabaseHandler(":memory:")

    def tearDown(self):
        self.db.close()

    def test_save_and_retrieve_vehicle(self):
        """Test that we can bulk insert vehicles and read them back."""
        ts = int(time.time())
        
        vehicle_data = [
            (ts, "route_4", "v_100", 47.4979, 19.0402),
            (ts, "route_6", "v_101", 47.5000, 19.0500)
        ]
        
        self.db.save_vehicles_bulk(vehicle_data)
        
        # ASSERT: Check if data is in DuckDB
        result = self.db.connection.execute("SELECT * FROM vehicle_positions ORDER BY vehicle_id").fetchall()
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0][2], "v_100") # Check first vehicle ID
        self.assertEqual(result[1][2], "v_101") # Check second vehicle ID

    def test_save_trip_updates(self):
        """Test that we can bulk insert trip updates."""
        # Tuple format: (timestamp, trip_id, route_id, stop_id, stop_seq, arr_delay, arr_time, dep_delay, dep_time)
        update_data = [
            (12345, "trip_1", "route_4", "stop_A", 1, 60, 0, 0, 0),
            (93111, "trip_2", "route_6", "stop_C", 3, 120, 0, 0, 0)
        ]

        self.db.save_trip_updates_bulk(update_data)

        result = self.db.connection.execute("SELECT * FROM trip_updates").fetchall()
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0][1], "trip_1")
        self.assertEqual(result[0][5], 60)
        self.assertEqual(result[1][3], "stop_C")
        self.assertEqual(result[1][4], 3)

if __name__ == '__main__':
    unittest.main()