import zipfile
import requests
import io
import pandas as pd
import json

STOPS_URL = "https://go.bkk.hu/api/static/v1/public-gtfs/budapest_gtfs.zip"
response = requests.get(STOPS_URL)

if response.status_code == 200:
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        if "stops.txt" in z.namelist():
            df = pd.read_csv(z.open("stops.txt"), usecols=["stop_id", "stop_name"])
            df = df.set_index("stop_id")
            stops_dict = df["stop_name"].to_dict()

            print("First 5 rows of stops dict:")
            print(df.head())

            with open('stop_names.json', 'w') as f:
                json.dump(stops_dict, f)

        else:
            print("Couldn't find 'stops.txt'")
else:
    print(f"Error. Status code: {response.status_code}")

