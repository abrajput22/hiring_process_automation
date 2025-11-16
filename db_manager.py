import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient


# Load environment variables
load_dotenv(override=False)

MONGO_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("MONGODB_DATABASE")

if not MONGO_URI or not DB_NAME:
    raise ValueError("MONGODB_URI and MONGODB_DATABASE must be set in environment/.env")


class Database:
    def __init__(self):
        self.client = None
        self.db = None
    
    def _ensure_client(self):
        if self.client is None:
            self.client = AsyncIOMotorClient(
                MONGO_URI,
                serverSelectionTimeoutMS=30000,
                connectTimeoutMS=20000,
                socketTimeoutMS=60000,
                maxPoolSize=5,
                minPoolSize=1,
                retryWrites=True,
                readPreference='primaryPreferred',
                w='majority',
                wtimeoutMS=30000,
                heartbeatFrequencyMS=10000,
                maxIdleTimeMS=30000
            )
            self.db = self.client[DB_NAME]

    async def get_collection(self, collection_name: str):
        self._ensure_client()
        return self.db[collection_name]
    
    async def health_check(self):
        """Check if database connection is healthy"""
        try:
            self._ensure_client()
            await self.client.admin.command('ping')
            return True
        except Exception as e:
            print(f"Database health check failed: {e}")
            return False


db_manager = Database()


async def print_all_candidates():
    try:
        collection = await db_manager.get_collection("candidate")
        candidates = await collection.find({}).to_list(length=None)
        print(f"Found {len(candidates)} candidates:")
        for candidate in candidates:
            print(candidate)
    except Exception as e:
        print(f"Error connecting to database: {e}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(print_all_candidates())


