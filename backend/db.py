import os
import sys
import hashlib
import hmac
from datetime import datetime
from typing import List, Dict, Optional
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError
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
        database.scans.create_index([("username", ASCENDING)])
        
        # User collection indexes
        database.users.create_index([("username", ASCENDING)], unique=True)
        database.users.create_index([("email", ASCENDING)], unique=True)
        print("[MongoDB] Collections and indexes initialized successfully")
    except Exception as e:
        print(f"[MongoDB Warning] Index creation notice: {e}")

# ==================== Authentication & User Operations ====================

def hash_password(password: str) -> str:
    """Hash password using SHA-256 with salt"""
    salt = "codereview_salt_2026"
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against stored hash"""
    return hmac.compare_digest(hash_password(password), hashed)

def create_user(username: str, email: str, password: str) -> Dict:
    """Register a new user in MongoDB"""
    database = get_database()
    doc = {
        "username": username.strip().lower(),
        "email": email.strip().lower(),
        "password_hash": hash_password(password),
        "created_at": datetime.now().isoformat()
    }
    try:
        database.users.insert_one(doc)
        doc.pop("_id", None)
        doc.pop("password_hash", None)
        return {"status": "success", "user": doc}
    except DuplicateKeyError as e:
        if "username" in str(e):
            return {"status": "error", "message": "Username already taken"}
        return {"status": "error", "message": "Email already registered"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_user_by_username(username: str) -> Optional[Dict]:
    """Retrieve user document by username"""
    database = get_database()
    try:
        return database.users.find_one({"username": username.strip().lower()}, {"_id": 0})
    except Exception as e:
        print(f"[MongoDB Error] Fetching user {username}: {e}")
        return None

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

def get_scans(limit: int = 50, username: Optional[str] = None) -> List[Dict]:
    """Retrieve scan history filtered by user when specified"""
    database = get_database()
    try:
        query = {}
        if username:
            query["username"] = username.strip().lower()
            
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
