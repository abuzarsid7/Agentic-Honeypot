# redis_client.py

import os
import redis
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

redis_client = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True  # store strings instead of bytes
)
print("Connected to Redis:", REDIS_URL)
print("Ping:", redis_client.ping())