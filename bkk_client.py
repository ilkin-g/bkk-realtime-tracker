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
        self.session = requests.Session()

    def fetch_vehicles(self, rids):
        try:
            response = self.session.get(self.VEHICLES_URL, timeout=10)

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
            response = self.session.get(self.UPDATES_URL, timeout=10)
            if response.status_code != 200:
                logging.warning(f"API returned status: {response.status_code}")
                return []
            
            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(response.content)

            timestamp = feed.header.timestamp
            trip_updates = []
            
            for entity in feed.entity:
                if entity.HasField("trip_update") and entity.trip_update.trip.route_id in rids:
                    tu = entity.trip_update
                    tid = tu.trip.trip_id
                    rid = tu.trip.route_id
                    
                    for stop in tu.stop_time_update:
                        # Initialize defaults
                        arr_delay = 0
                        arr_time = 0
                        dep_delay = 0
                        dep_time = 0
                        sid = stop.stop_id
                        stop_seq = stop.stop_sequence

                        # CAPTURE ARRIVAL
                        if stop.HasField("arrival"):
                            if stop.arrival.HasField("delay"):
                                arr_delay = stop.arrival.delay
                            if stop.arrival.HasField("time"):
                                arr_time = stop.arrival.time

                        # CAPTURE DEPARTURE
                        if stop.HasField("departure"):
                            if stop.departure.HasField("delay"):
                                dep_delay = stop.departure.delay
                            if stop.departure.HasField("time"):
                                dep_time = stop.departure.time

                        if arr_delay != 0 or arr_time != 0 or dep_delay != 0 or dep_time != 0:
                            trip_updates.append((timestamp, tid, rid, sid, stop_seq, arr_delay, arr_time, dep_delay, dep_time))

            return trip_updates
        
        except requests.exceptions.RequestException as e:
            logging.error(f"Network error fetching trip updates: {e}")
            return []