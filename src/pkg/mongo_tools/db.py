from pymongo.errors import PyMongoError
from motor.motor_asyncio import AsyncIOMotorClient
from core.config import MONGO_URI, MONGO_NAME, MONGO_USER, MONGO_PASSWORD
from api.utils.logger import PollLogger
from datetime import datetime

# Logging
logger = PollLogger(__name__)




# class MongoDB:
#     def __init__(self):
#         try:
#             self.async_client = AsyncIOMotorClient(
#                 MONGO_URI,
#                 username=MONGO_USER,
#                 password=MONGO_PASSWORD,
#
#             )
#             self.async_db = self.async_client[MONGO_NAME]
#
#             # Используем кастомный логгер для этого класса
#             self._logger = logger.getChild("MongoDB")
#             self._logger.info("Successfully connected to MongoDB.")
#         except PyMongoError as e:
#             self._logger.error(f"Error connecting to MongoDB: {e}")
#
#     def close_connections(self):
#         self._logger.info("Closing MongoDB connections.")
#         self.async_client.close()
#         self._logger.info("Successfully closed MongoDB connections.")
#
#     async def find_one(self, collection, query):
#         try:
#             return await self.async_db[collection].find_one(query)
#         except PyMongoError as e:
#             self._logger.error(f"Error in find_one: {e}")
#             return None
#
#     async def find_all(self, collection, query=None):
#         try:
#             cursor = self.async_db[collection].find(query) if query else self.async_db[collection].find()
#             return await cursor.to_list(length=None)
#         except PyMongoError as e:
#             self._logger.error(f"Error in find_all: {e}")
#             return None
#
#     async def insert_one(self, collection, document):
#         try:
#             result = await self.async_db[collection].insert_one(document)
#             return result.inserted_id
#         except PyMongoError as e:
#             self._logger.error(f"Error in find_all: {e}")
#             return None
#
#     async def update_one(self, collection, query, update):
#         try:
#             result = await self.async_db[collection].update_one(query, {"$set": update})
#             return result.modified_count
#         except PyMongoError as e:
#             self._logger.error(f"Error in find_all: {e}")
#             return None
#
#     async def delete_one(self, collection, query):
#         try:
#             result = await self.async_db[collection].delete_one(query)
#             return result.deleted_count
#         except PyMongoError as e:
#             self._logger.error(f"Error in find_all: {e}")
#             return None
#
#     async def count_poll_sessions(self, poll_uuid):
#         return await self.async_db["sessions"].count_documents({"poll_uuid": poll_uuid})


# class DatabaseManager:
#     def __init__(self):
#         self.client = None
#         self.db = None
#
#     async def connect_to_database(self):
#         if MONGO_URI and MONGO_NAME and MONGO_USER and MONGO_PASSWORD:
#             self.client = AsyncIOMotorClient(
#                 MONGO_URI,
#                 username=MONGO_USER,
#                 password=MONGO_PASSWORD,
#             )
#             self.db = self.client[MONGO_NAME]
#             logger.info(f"Connected to MongoDB from startup!")
#
#     async def close_database_connection(self):
#         if self.client:
#             self.client.close()
#             logger.info("Closed MongoDB connection.")
#
#     async def insert_one(self, collection, document):
#         try:
#             result = await self.db[collection].insert_one(document)
#             return result.inserted_id
#         except PyMongoError as e:
#             logger.error(f"Error in find_all: {e}")
#             return None
#
#     async def find_one(self, collection, query):
#         try:
#             return await self.db[collection].find_one(query)
#         except PyMongoError as e:
#             logger.error(f"Error in find_one: {e}")
#             return None
#
#     async def find_all(self, collection, query=None):
#         try:
#             cursor = self.db[collection].find(query) if query else self.db[collection].find()
#             return await cursor.to_list(length=None)
#         except PyMongoError as e:
#             logger.error(f"Error in find_all: {e}")
#             return None
#
#     async def update_one(self, collection, query, update):
#         try:
#             result = await self.db[collection].update_one(query, {"$set": update})
#             return result.modified_count
#         except PyMongoError as e:
#             logger.error(f"Error in find_all: {e}")
#             return None
#
#     async def delete_one(self, collection, query):
#         try:
#             result = await self.db[collection].delete_one(query)
#             return result.deleted_count
#         except PyMongoError as e:
#             logger.error(f"Error in find_all: {e}")
#             return None
#
#     async def count_poll_sessions(self, poll_uuid):
#         return await self.db["sessions"].count_documents({"poll_uuid": poll_uuid})
#
#     def get_database(self):
#         return self.db


# mongo_manager = DatabaseManager()


client = AsyncIOMotorClient(
                MONGO_URI,
                username=MONGO_USER,
                password=MONGO_PASSWORD,
            )
database = client[MONGO_NAME]
session_collection = database.get_collection("sessions")


def session_helper(session) -> dict:
    return {
        "token": str(session["token"]),
        "fingerprint": str(session["fingerprint"]),
        "poll_uuid": str(session["poll_uuid"]),
        "expires_at": datetime.strptime(session.get("expires_at", ""), "%Y-%m-%dT%H:%M:%S")
        if session.get("expires_at") else None,
        "expired": session.get("expired", False),
        "answered": session.get("answered", False)
    }
