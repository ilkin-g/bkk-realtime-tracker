from database import DatabaseHandler
from bkk_client import BKKClient
import logging
import time
import sys

def main():
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

    db = DatabaseHandler("bkk.db")
    client = BKKClient()
    
    TARGETS = ("3040", "3060") 

    logging.info("Database connected. Client initialized.")

    try:
        while True:
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
            
            logging.info("Batch complete. Sleeping for 30 seconds...")
            time.sleep(30)

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