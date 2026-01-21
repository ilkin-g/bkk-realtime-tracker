import requests
import os
import logging
from dotenv import load_dotenv
from google.transit import gtfs_realtime_pb2

class BKKClient:

    def __init__(self):
        load_dotenv()

        API_KEY = os.getenv("BKK_API")
        self.VEHICLES_URL = f"https://go.bkk.hu/api/query/v1/ws/gtfs-rt/full/VehiclePositions.pb?key={API_KEY}"
        self.UPDATES_URL = f"https://go.bkk.hu/api/query/v1/ws/gtfs-rt/full/TripUpdates.pb?key={API_KEY}"

    def fetch_vehicles(self, rids):
        try:
            response = requests.get(self.VEHICLES_URL, timeout=10)

            if response.status_code != 200:
                logging.warning(f"API returned status: {response.status_code}")
                return []

            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(response.content)

            timestamp = feed.header.timestamp

            vehicles = []
            for entity in feed.entity:
                if entity.HasField("vehicle") and entity.vehicle.trip.route_id in rids:
                    ev = entity.vehicle
                    rid = ev.trip.route_id
                    vid = ev.vehicle.id
                    lat = ev.position.latitude
                    lon = ev.position.longitude

                    vehicles.append((timestamp, rid, vid, lat, lon))

            return vehicles
        except requests.exceptions.RequestException as e:
            logging.error(f"Network error fetching vehicles: {e}")
            return []

    def fetch_trip_updates(self, rids):
        try:
            response = requests.get(self.UPDATES_URL, timeout=10)

            if response.status_code != 200:
                logging.warning(f"API returned status: {response.status_code}")
                return []
            
            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(response.content)

            timestamp = feed.header.timestamp

            trip_updates = []
            for entity in feed.entity:
                    if entity.HasField("trip_update") and entity.trip_update.trip.route_id in rids:
                        tid = entity.trip_update.trip.trip_id
                        rid = entity.trip_update.trip.route_id
                        
                        for stop in entity.trip_update.stop_time_update:
                            arrival_delay = 0
                            departure_delay = 0
                            stop_update = stop.stop_sequence

                            if stop.HasField("arrival"):
                                arrival_delay = stop.arrival.delay if stop.arrival.delay else 0

                            if stop.HasField("departure") and stop.departure.delay != 0:
                                departure_delay = stop.departure.delay if stop.departure.delay else 0               

                            trip_updates.append((timestamp, tid, rid, stop_update, arrival_delay, departure_delay))

            return trip_updates
        
        except requests.exceptions.RequestException as e:
            logging.error("Network error fetching trip updates: {e}")
            return []