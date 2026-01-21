from database import DatabaseHandler
from bkk_client import BKKClient
import logging
import time

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
    TARGETS = ("3040", "4060")

    logging.info("Database connected. Client initalized.")

    while True:
        try:
            logging.info("Starting batch fetch...")
            # 1. Get vehicles
            vehicles = client.fetch_vehicles(TARGETS)
            logging.info(f"Found {len(vehicles)} active.")
            
            for vehicle in vehicles:
                db.save_vehicle(vehicle[0], vehicle[1], vehicle[2], vehicle[3], vehicle[4])

            # 2. Get trip updates
            updates = client.fetch_trip_updates(TARGETS)
            logging.info(f"Found {len(updates)} trip updates.")

            for update in updates:
                db.save_trip_update(update[0], update[1], update[2], update[3], update[4], update[5])
            print("Batch complete. Sleeping for 30 seconds...")
        
        except Exception as e:
            logging.exception("Critical failure!")
            print(f"Error: {e}")

        time.sleep(30)

if __name__ == "__main__":
    main()