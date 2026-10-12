import json
import logging
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import pymongo
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from backend.app.config import settings

logger = logging.getLogger("codereview.db")

class LocalCollectionFallback:
    """Thread-safe JSON-persisted fallback for MongoDB collections."""
    def __init__(self, name: str, storage_file: Path):
        self.name = name
        self.storage_file = storage_file
        self._lock = threading.RLock()
        self._docs: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        with self._lock:
            if self.storage_file.exists():
                try:
                    with open(self.storage_file, "r", encoding="utf-8") as f:
                        self._docs = json.load(f)
                except Exception as e:
                    logger.warning(f"Failed to read local store for {self.name}: {e}")
                    self._docs = []
            else:
                self._docs = []

    def _save(self):
        with self._lock:
            try:
                self.storage_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.storage_file, "w", encoding="utf-8") as f:
                    json.dump(self._docs, f, default=str, indent=2)
            except Exception as e:
                logger.error(f"Failed to save local store for {self.name}: {e}")

    def _match(self, doc: Dict[str, Any], query: Dict[str, Any]) -> bool:
        if not query:
            return True
        for k, v in query.items():
            if k == "$or" and isinstance(v, list):
                if not any(self._match(doc, q) for q in v):
                    return False
                continue
            if k == "$and" and isinstance(v, list):
                if not all(self._match(doc, q) for q in v):
                    return False
                continue
            
            doc_val = doc.get(k)
            if isinstance(v, dict):
                for op, op_val in v.items():
                    if op == "$eq" and doc_val != op_val:
                        return False
                    elif op == "$ne" and doc_val == op_val:
                        return False
                    elif op == "$in" and (doc_val not in op_val if isinstance(op_val, list) else True):
                        return False
                    elif op == "$nin" and (doc_val in op_val if isinstance(op_val, list) else False):
                        return False
                    elif op == "$gt" and not (doc_val is not None and doc_val > op_val):
                        return False
                    elif op == "$gte" and not (doc_val is not None and doc_val >= op_val):
                        return False
                    elif op == "$lt" and not (doc_val is not None and doc_val < op_val):
                        return False
                    elif op == "$lte" and not (doc_val is not None and doc_val <= op_val):
                        return False
                    elif op == "$regex":
                        import re
                        pattern = re.compile(str(op_val), re.IGNORECASE)
                        if not pattern.search(str(doc_val or "")):
                            return False
            else:
                if doc_val != v:
                    return False
        return True

    def insert_one(self, doc: Dict[str, Any]):
        with self._lock:
            item = dict(doc)
            if "_id" not in item:
                item["_id"] = str(uuid.uuid4())
            self._docs.append(item)
            self._save()
            class InsertResult:
                inserted_id = item["_id"]
            return InsertResult()

    def insert_many(self, docs: List[Dict[str, Any]]):
        with self._lock:
            inserted_ids = []
            for doc in docs:
                item = dict(doc)
                if "_id" not in item:
                    item["_id"] = str(uuid.uuid4())
                self._docs.append(item)
                inserted_ids.append(item["_id"])
            self._save()
            class InsertManyResult:
                pass
            res = InsertManyResult()
            res.inserted_ids = inserted_ids
            return res

    def find_one(self, query: Optional[Dict[str, Any]] = None, projection: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        with self._lock:
            query = query or {}
            for doc in self._docs:
                if self._match(doc, query):
                    return self._apply_projection(doc, projection)
            return None

    def find(self, query: Optional[Dict[str, Any]] = None, projection: Optional[Dict[str, Any]] = None):
        with self._lock:
            query = query or {}
            matched = [self._apply_projection(d, projection) for d in self._docs if self._match(d, query)]
            
            class Cursor:
                def __init__(self, items):
                    self.items = list(items)
                
                def sort(self, key_or_list, direction=1):
                    def _sort_key(val):
                        if val is None:
                            return ""
                        if hasattr(val, "isoformat"):
                            return val.isoformat()
                        return str(val)

                    if isinstance(key_or_list, list):
                        for k, d in reversed(key_or_list):
                            self.items.sort(key=lambda x: _sort_key(x.get(k)), reverse=(d == -1 or d == pymongo.DESCENDING))
                    elif isinstance(key_or_list, str):
                        self.items.sort(key=lambda x: _sort_key(x.get(key_or_list)), reverse=(direction == -1 or direction == pymongo.DESCENDING))
                    return self
                
                def limit(self, count: int):
                    self.items = self.items[:count]
                    return self
                
                def skip(self, count: int):
                    self.items = self.items[count:]
                    return self
                
                def __iter__(self):
                    return iter(self.items)
                
                def __list__(self):
                    return list(self.items)

            return Cursor(matched)

    def _apply_projection(self, doc: Dict[str, Any], projection: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not projection:
            return dict(doc)
        res = {}
        for k, v in doc.items():
            if projection.get(k, 0) == 1 or (projection.get("_id", 1) == 1 and k == "_id"):
                res[k] = v
        return res

    def count_documents(self, query: Optional[Dict[str, Any]] = None) -> int:
        with self._lock:
            query = query or {}
            return sum(1 for d in self._docs if self._match(d, query))

    def update_one(self, query: Dict[str, Any], update: Dict[str, Any]):
        with self._lock:
            for i, doc in enumerate(self._docs):
                if self._match(doc, query):
                    if "$set" in update:
                        for k, v in update["$set"].items():
                            self._docs[i][k] = v
                    if "$inc" in update:
                        for k, v in update["$inc"].items():
                            self._docs[i][k] = self._docs[i].get(k, 0) + v
                    self._save()
                    class UpdateResult:
                        modified_count = 1
                    return UpdateResult()
            class UpdateResult:
                modified_count = 0
            return UpdateResult()

    def update_many(self, query: Dict[str, Any], update: Dict[str, Any]):
        with self._lock:
            count = 0
            for i, doc in enumerate(self._docs):
                if self._match(doc, query):
                    if "$set" in update:
                        for k, v in update["$set"].items():
                            self._docs[i][k] = v
                    if "$inc" in update:
                        for k, v in update["$inc"].items():
                            self._docs[i][k] = self._docs[i].get(k, 0) + v
                    count += 1
            if count > 0:
                self._save()
            class UpdateResult:
                modified_count = count
            return UpdateResult()

    def delete_one(self, query: Dict[str, Any]):
        with self._lock:
            for i, doc in enumerate(self._docs):
                if self._match(doc, query):
                    self._docs.pop(i)
                    self._save()
                    class DeleteResult:
                        deleted_count = 1
                    return DeleteResult()
            class DeleteResult:
                deleted_count = 0
            return DeleteResult()

    def delete_many(self, query: Dict[str, Any]):
        with self._lock:
            before = len(self._docs)
            self._docs = [d for d in self._docs if not self._match(d, query)]
            after = len(self._docs)
            if before != after:
                self._save()
            class DeleteResult:
                deleted_count = before - after
            return DeleteResult()

    def distinct(self, key: str, query: Optional[Dict[str, Any]] = None) -> List[Any]:
        with self._lock:
            query = query or {}
            vals = set()
            for doc in self._docs:
                if self._match(doc, query):
                    v = doc.get(key)
                    if v is not None:
                        if isinstance(v, list):
                            vals.update(v)
                        else:
                            vals.add(v)
            return list(vals)

    def create_index(self, keys, **kwargs):
        # Fallback index stub
        pass


class Database:
    def __init__(self):
        self.is_connected: bool = False
        self.use_fallback: bool = False
        self.client: Optional[pymongo.MongoClient] = None
        self.db: Any = None
        self._fallback_collections: Dict[str, LocalCollectionFallback] = {}
        self.fallback_dir = settings.DATA_DIR / "local_db"
        self.fallback_dir.mkdir(parents=True, exist_ok=True)

    def connect(self):
        try:
            logger.info(f"Connecting to MongoDB at {settings.MONGODB_URI}...")
            self.client = pymongo.MongoClient(
                settings.MONGODB_URI,
                serverSelectionTimeoutMS=1500,
                connectTimeoutMS=1500
            )
            # Test ping
            self.client.admin.command('ping')
            self.db = self.client[settings.MONGODB_DB_NAME]
            self.is_connected = True
            self.use_fallback = False
            logger.info("Successfully connected to MongoDB!")
            self._init_indexes()
        except (ConnectionFailure, ServerSelectionTimeoutError, Exception) as e:
            logger.warning(f"MongoDB not reachable ({e}). Initializing high-performance local document store fallback.")
            self.is_connected = True
            self.use_fallback = True

    def _init_indexes(self):
        if not self.use_fallback and self.db is not None:
            try:
                self.db.scans.create_index([("scan_id", pymongo.ASCENDING)], unique=True)
                self.db.scans.create_index([("created_at", pymongo.DESCENDING)])
                self.db.findings.create_index([("scan_id", pymongo.ASCENDING), ("severity", pymongo.ASCENDING)])
                self.db.findings.create_index([("rule_id", pymongo.ASCENDING)])
                self.db.governance_policies.create_index([("policy_id", pymongo.ASCENDING)], unique=True)
                self.db.governance_events.create_index([("timestamp", pymongo.DESCENDING)])
                self.db.ai_reviews.create_index([("scan_id", pymongo.ASCENDING)])
                self.db.audit_logs.create_index([("timestamp", pymongo.DESCENDING)])
                logger.info("MongoDB indexes verified.")
            except Exception as e:
                logger.warning(f"Index creation warning: {e}")

    def get_collection(self, name: str):
        if not self.is_connected:
            self.connect()

        if not self.use_fallback and self.db is not None:
            return self.db[name]
        
        if name not in self._fallback_collections:
            storage_file = self.fallback_dir / f"{name}.json"
            self._fallback_collections[name] = LocalCollectionFallback(name, storage_file)
        return self._fallback_collections[name]

    @property
    def scans(self):
        return self.get_collection("scans")

    @property
    def findings(self):
        return self.get_collection("findings")

    @property
    def projects(self):
        return self.get_collection("projects")

    @property
    def scan_jobs(self):
        return self.get_collection("scan_jobs")

    @property
    def governance_policies(self):
        return self.get_collection("governance_policies")

    @property
    def governance_events(self):
        return self.get_collection("governance_events")

    @property
    def ai_reviews(self):
        return self.get_collection("ai_reviews")

    @property
    def audit_logs(self):
        return self.get_collection("audit_logs")

    @property
    def users(self):
        return self.get_collection("users")


db = Database()
