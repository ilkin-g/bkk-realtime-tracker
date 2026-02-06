import zipfile
import requests
import io
import pandas as pd
import json
import time
from requests.exceptions import ChunkedEncodingError, RequestException, IncompleteRead

STOPS_URL = "https://go.bkk.hu/api/static/v1/public-gtfs/budapest_gtfs.zip"

def download_with_retry(url, retries=3, delay=5):
    """
    Downloads data with automatic retries for flaky Docker networks.
    """
    for i in range(retries):
        try:
            print(f"Attempt {i+1}/{retries}: Downloading GTFS data...")
            response = requests.get(url, stream=False, timeout=60)

            if response.status_code == 200:
                print("Download successful.")
                return response.content
            else:
                print(f"Server returned status: {response.status_code}")

        except (ChunkedEncodingError, IncompleteRead, RequestException) as e:
            print(f"Network error: {e}")
            if i < retries - 1:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print("Max retries reached.")
                raise e
    
    raise Exception("Failed to download GTFS data.")

def main():
    try:
        # 1. Download with retry
        content = download_with_retry(STOPS_URL)

        # 2. Process the Zip file
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            if "stops.txt" in z.namelist():
                print("📖 Reading stops.txt...")
                df = pd.read_csv(z.open("stops.txt"), usecols=["stop_id", "stop_name"])
                
                # Create dictionary
                df = df.set_index("stop_id")
                stops_dict = df["stop_name"].to_dict()

                print(f"Found {len(stops_dict)} stops. First 5:")
                print(df.head())

                # 3. Save to JSON
                print("Saving to stop_names.json...")
                with open('stop_names.json', 'w') as f:
                    json.dump(stops_dict, f)
                
                print("Done!")

            else:
                print("Error: Couldn't find 'stops.txt' in the downloaded zip.")
                
    except Exception as e:
        print(f"Critical Failure: {e}")

if __name__ == "__main__":
    main()