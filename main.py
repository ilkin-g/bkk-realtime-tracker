from database import DatabaseHandler
from bkk_client import BKKClient
import logging
import time
import sys
import yaml

def main():
    # Load yaml file
    with open ("config.yaml", "r") as f:
        config = yaml.safe_load(f)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler("pipeline.log"),
            logging.StreamHandler()
        ]
    )

    logging.info("Pipeline starting up...")

    db_path = config["database"]["path"]
    db = DatabaseHandler(db_path)
    client = BKKClient()
    
    TARGETS = config["transit"]["target_routes"]

    logging.info("Database connected. Client initialized.")

    try:
        while True:
            start_time = time.time()
            logging.info("Starting batch fetch...")
            
            # 1. Get vehicles
            vehicles = client.fetch_vehicles(TARGETS)
            logging.info(f"Found {len(vehicles)} active vehicles.")
            
            for vehicle in vehicles:
                db.save_vehicle(*vehicle)

            # 2. Get trip updates
            updates = client.fetch_trip_updates(TARGETS)
            logging.info(f"Found {len(updates)} trip updates.")

            for update in updates:
                db.save_trip_update(*update)
            
            elapsed = time.time() - start_time
            fetch_interval = config["transit"]["fetch_interval"]
            sleep_time = max(0, fetch_interval - elapsed)

            logging.info(f"Batch finished in {elapsed:.2f} seconds. Sleeping for {sleep_time:.2f} seconds...")
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        logging.info("User stopped script (Ctrl+C). Closing DB...")
        db.close()
        sys.exit(0)
    except Exception as e:
        logging.exception("Critical failure!")
        print(f"Error: {e}")
        db.close()

if __name__ == "__main__":
    main()