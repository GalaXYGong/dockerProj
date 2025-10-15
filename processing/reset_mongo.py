import yaml
import time
import logging.config
from pymongo import MongoClient

# --- Configuration Loading ---
# Assume app_conf.yml and log_conf.yml are in the same directory
try:
    with open('./app_conf.yml','r') as f:
        app_config = yaml.safe_load(f.read())

    with open("log_conf.yml", "r") as f:
        LOG_CONFIG = yaml.safe_load(f.read())
        logging.config.dictConfig(LOG_CONFIG)
except FileNotFoundError as e:
    print(f"Error: Configuration file not found. Ensure app_conf.yml and log_conf.yml are present. {e}")
    exit(1)

logger = logging.getLogger('basicLogger')

# --- MongoDB Initialization ---
MONGO_CONF = app_config['mongodb']
MONGO_URL = f"mongodb://{MONGO_CONF['hostname']}:{MONGO_CONF['port']}/"
DB_NAME = MONGO_CONF['db']
COLLECTION_NAME = MONGO_CONF['collection']

def drop_and_reset_stats():
    """
    Connects to MongoDB and permanently deletes the statistics collection.
    """
    MAX_RETRIES = 5
    RETRY_DELAY = 3
    client = None

    # Connect to MongoDB with retries
    for i in range(MAX_RETRIES):
        try:
            client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
            client.admin.command('ismaster') 
            db = client[DB_NAME]
            stats_collection = db[COLLECTION_NAME]
            
            logger.info(f"Successfully connected to MongoDB at {MONGO_URL}. Proceeding to drop collection.")
            
            # --- CRITICAL DROP OPERATION ---
            stats_collection.drop()
            logger.info(f"SUCCESS: Collection '{COLLECTION_NAME}' in database '{DB_NAME}' has been DROPPED.")
            logger.info("The statistics collection is now empty.")
            
            # --- NEXT STEP INSTRUCTIONS ---
            logger.info("--------------------------------------------------")
            logger.info("Next Step: Restart the processing/app.py service.")
            logger.info("The scheduler will now start from a clean slate (last_updated=0) and recalculate ALL stats from MySQL, using the fixed logic.")
            logger.info("--------------------------------------------------")
            return

        except Exception as e:
            logger.warning(f"Connection/Drop failed (Attempt {i+1}/{MAX_RETRIES}). Retrying in {RETRY_DELAY} seconds: {e}")
            time.sleep(RETRY_DELAY)
            
    logger.error("FATAL: Failed to connect or drop collection after multiple retries.")


if __name__ == "__main__":
    drop_and_reset_stats()
