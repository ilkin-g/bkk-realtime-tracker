import io
import zipfile
import requests
import duckdb
import pandas as pd
import yaml
import os

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)
DB_PATH = config['database']['path']

URL = "https://go.bkk.hu/api/static/v1/public-gtfs/budapest_gtfs.zip"
print(f"⬇️ Downloading GTFS data...")
response = requests.get(URL)

if response.status_code != 200:
    print("Failed to download.")
    exit()

with zipfile.ZipFile(io.BytesIO(response.content)) as z:
    print("Reading trips.txt...")
    trip_df = pd.read_csv(z.open("trips.txt"), dtype=str)
    
    targets = config['transit'].get('target_routes', ['3040', '3060'])
    trip_df = trip_df[trip_df["route_id"].isin(targets)]
    valid_trips = set(trip_df["trip_id"])
    print(f"Found {len(valid_trips)} target trips.")

    print("⏳ Reading stop_times.txt...")
    schedule_df = pd.read_csv(
        z.open("stop_times.txt"), 
        usecols=["trip_id", "arrival_time", "stop_id", "stop_sequence"],
        dtype=str
    )

    schedule_df = schedule_df[schedule_df["trip_id"].isin(valid_trips)]
    print(f"Filtered to {len(schedule_df)} schedule rows.")

    if "stops.txt" in z.namelist():
        print("🚏 Reading stops.txt...")
        stops_df = pd.read_csv(
            z.open("stops.txt"), 
            usecols=["stop_id", "stop_name"],
            dtype=str
        )
        print(f"Found {len(stops_df)} stop definitions.")
    else:
        print("stops.txt missing!")
        stops_df = pd.DataFrame()

    print(f"💾 Writing to {DB_PATH}...")
    conn = duckdb.connect(DB_PATH)
    
    conn.execute("DROP TABLE IF EXISTS static_schedule")
    conn.execute("CREATE TABLE static_schedule AS SELECT * FROM schedule_df")
    
    if not stops_df.empty:
        conn.execute("DROP TABLE IF EXISTS stops")
        conn.execute("CREATE TABLE stops AS SELECT * FROM stops_df")

    count_sched = conn.execute("SELECT count(*) FROM static_schedule").fetchone()[0]
    count_stops = conn.execute("SELECT count(*) FROM stops").fetchone()[0]
    conn.close()
    
    print(f"SUCCESS! Database now contains:")
    print(f"   - {count_sched} schedule rows")
    print(f"   - {count_stops} stop definitions")