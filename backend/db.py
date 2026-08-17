import os
import sys
from datetime import datetime
from typing import List, Dict, Optional
from pymongo import MongoClient, ASCENDING, DESCENDING
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/codereview_db")

client: Optional[MongoClient] = None
db = None

def get_database():
    """
    Lazy initialization of MongoDB client and database connection
    """
    global client, db
    if db is not None:
        return db
    
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        try:
            db_name = client.get_default_database().name
        except Exception:
            db_name = "codereview_db"
            
        db = client[db_name]
        return db
    except Exception as e:
        print(f"[MongoDB Warning] Connection failed: {e}")
        client = MongoClient("mongodb://localhost:27017/codereview_db", serverSelectionTimeoutMS=2000)
        db = client["codereview_db"]
        return db

def init_db():
    """
    Initialize database collections and indexes
    """
    try:
        database = get_database()
        database.scans.create_index([("scan_id", ASCENDING)], unique=True)
        database.scans.create_index([("timestamp", DESCENDING)])
        print("[MongoDB] Collections and indexes initialized successfully")
    except Exception as e:
        print(f"[MongoDB Warning] Index creation notice: {e}")

# ==================== Scan History Operations ====================

def save_scan(scan_result: Dict) -> Dict:
    """Store scan result into MongoDB scans collection"""
    database = get_database()
    try:
        record = dict(scan_result)
        if "_id" in record:
            del record["_id"]
        
        database.scans.insert_one(record)
        record.pop("_id", None)
        return {"status": "success", "scan": record}
    except Exception as e:
        print(f"[MongoDB Error] Saving scan: {e}")
        return {"status": "error", "message": str(e)}

def get_scans(limit: int = 50, project_name: Optional[str] = None) -> List[Dict]:
    """Retrieve scan history"""
    database = get_database()
    try:
        query = {}
        if project_name:
            query["project_name"] = project_name
            
        scans = list(database.scans.find(query, {"_id": 0}).sort("timestamp", DESCENDING).limit(limit))
        return scans
    except Exception as e:
        print(f"[MongoDB Error] Fetching scans: {e}")
        return []

def get_scan_by_id(scan_id: str) -> Optional[Dict]:
    """Retrieve scan result by ID"""
    database = get_database()
    try:
        return database.scans.find_one({"scan_id": scan_id}, {"_id": 0})
    except Exception as e:
        print(f"[MongoDB Error] Fetching scan {scan_id}: {e}")
        return None
