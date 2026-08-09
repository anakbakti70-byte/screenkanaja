import redis
import os
from dotenv import load_dotenv

load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

class RedisClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisClient, cls).__new__(cls)
            try:
                cls._instance.client = redis.Redis(
                    host=REDIS_HOST,
                    port=REDIS_PORT,
                    db=REDIS_DB,
                    password=REDIS_PASSWORD,
                    decode_responses=False
                )
                # Test connection
                cls._instance.client.ping()
            except redis.ConnectionError:
                print(f"Warning: Could not connect to Redis at {REDIS_HOST}:{REDIS_PORT}. Redis caching will be disabled.")
                cls._instance.client = None
        return cls._instance

    def get_client(self):
        return self.client

redis_client = RedisClient().get_client()
