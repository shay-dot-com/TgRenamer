from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ReturnDocument
from config import Config
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, uri, database_name):
        self._client = AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        
        # Collections
        self.queue = self.db.queue
        self.users = self.db.users

    async def add_to_queue(self, user_id, message_id, file_id, file_type):
        """Adds a new file to the persistent processing queue"""
        doc = {
            "user_id": user_id,
            "message_id": message_id,
            "file_id": file_id,
            "file_type": file_type,
            "status": "PENDING", # PENDING, PROCESSING, COMPLETED, FAILED, CANCELLED
            "status_msg_id": None
        }
        await self.queue.insert_one(doc)
        return doc

    async def get_next_job(self):
        """Atomically fetches a PENDING item and marks it PROCESSING"""
        doc = await self.queue.find_one_and_update(
            {"status": "PENDING"},
            {"$set": {"status": "PROCESSING"}},
            return_document=ReturnDocument.AFTER
        )
        return doc

    async def get_pending_files(self):
        """Fetches files that are pending or stuck in processing from a crash"""
        return await self.queue.find({"status": {"$in": ["PENDING", "PROCESSING"]}}).to_list(length=None)

    async def update_status(self, document_id, new_status):
        await self.queue.update_one({"_id": document_id}, {"$set": {"status": new_status}})

    async def save_status_message(self, document_id, msg_id):
        await self.queue.update_one({"_id": document_id}, {"$set": {"status_msg_id": msg_id}})

    # --- Thumbnail Logic ---
    async def set_thumbnail(self, user_id, file_id):
        await self.users.update_one(
            {"_id": user_id}, 
            {"$set": {"thumbnail": file_id}}, 
            upsert=True
        )

    async def get_thumbnail(self, user_id):
        user = await self.users.find_one({"_id": user_id})
        return user.get("thumbnail") if user else None

    async def delete_thumbnail(self, user_id):
        await self.users.update_one(
            {"_id": user_id},
            {"$unset": {"thumbnail": ""}}
        )

# Initialize global db instance
if Config.MONGO_URI:
    db = Database(Config.MONGO_URI, Config.DB_NAME)
else:
    logger.warning("MONGO_URI not provided. Database features will fail.")
    db = None
