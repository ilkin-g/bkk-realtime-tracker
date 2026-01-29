import json
import sqlite3
import pandas as pd
from datetime import datetime

try:
    with open("stop_names.json") as f:
        STOP_NAMES = json.load(f)

except Exception as e:
    print(f"Error during reading json: {e}")

else:
    print("Successfully read stop_names.json!")

query = """
    SELECT DISTINCT
        trip_id, arrival_time, stop_id
    FROM
        trip_updates
    WHERE
        stop_sequence = 10
"""

connection = sqlite3.connect("bkk.db")
cursor = connection.cursor()
cursor.execute(query)

rows = cursor.fetchall()
cols = [col[0] for col in cursor.description]

df = pd.DataFrame(rows, columns=cols)
df = df.drop_duplicates(subset=['trip_id'], keep='last')
df['time_readable'] = pd.to_datetime(df['arrival_time'], unit='s')

stop_id = df["stop_id"].iloc[0]
stop_name = STOP_NAMES[stop_id]

target_stop_id = 'F01111' 
df = df[df['stop_id'] == target_stop_id]

df = df.sort_values(by="arrival_time")
df["prev_arrival"] = df["arrival_time"].shift(1)
df["headway"] = df["arrival_time"] - df["prev_arrival"]
df["headway_minutes"] = (df["headway"] / 60).round(1)
df = df.dropna(subset=["headway_minutes"])

print(f"Stop: {stop_name}")
print(df.tail(25))