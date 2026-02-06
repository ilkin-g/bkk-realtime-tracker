import unittest
from unittest.mock import MagicMock, patch
from google.transit import gtfs_realtime_pb2
from src.client import BKKClient

class TestBKKClient(unittest.TestCase):

    @patch('src.client.requests.Session')
    def test_fetch_vehicles_parsing(self, mock_session_cls):
        """Test that we correctly parse a binary Protobuf response."""
        
        # 1. Create a Fake GTFS-RT Feed Message
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "2.0"
        feed.header.timestamp = 1700000000
        
        # Add a valid vehicle
        entity = feed.entity.add()
        entity.id = "1"
        entity.vehicle.trip.route_id = "4"
        entity.vehicle.vehicle.id = "tram_100"
        entity.vehicle.position.latitude = 47.5
        entity.vehicle.position.longitude = 19.1
        
        # Add a vehicle from WRONG route
        entity2 = feed.entity.add()
        entity2.id = "2"
        entity2.vehicle.trip.route_id = "999"
        entity2.vehicle.vehicle.id = "bus_200"
        
        # 2. Setup the Mock Response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = feed.SerializeToString()
        
        # Wire up the session mock
        mock_session_instance = mock_session_cls.return_value
        mock_session_instance.get.return_value = mock_response

        # 3. Run the Client
        client = BKKClient()
        vehicles = client.fetch_vehicles(rids=["4"])

        # 4. Assertions
        self.assertEqual(len(vehicles), 1)
        
        ts, rid, vid, lat, lon = vehicles[0]
        self.assertEqual(rid, "4")
        self.assertEqual(vid, "tram_100")
        self.assertEqual(lat, 47.5)

    @patch('src.client.requests.Session')
    def test_api_failure_handling(self, mock_session_cls):
        """Test that client returns empty list on API error."""
        
        # Setup mock to fail (404 error)
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        mock_session_instance = mock_session_cls.return_value
        mock_session_instance.get.return_value = mock_response

        client = BKKClient()
        vehicles = client.fetch_vehicles(rids=["4"])

        self.assertEqual(vehicles, [])

if __name__ == '__main__':
    unittest.main()