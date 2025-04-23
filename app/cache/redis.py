from typing import Optional

import orjson
import redis.asyncio as aioredis
from redis.asyncio.client import Redis

from app.core.config import settings


class RedisCache:
    """
    Asynchronous Redis cache wrapper for storing and retrieving JSON data.

    Provides simple `get` and `set` methods with automatic serialization,
    and manages connection lifecycle internally.
    """

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis: Redis

    async def connect(self) -> None:
        """
        Initialize the connection to the Redis server.
        """
        self.redis = await aioredis.from_url(self.redis_url, decode_responses=True)

    async def close(self) -> None:
        """
        Close the connection to the Redis server.
        """
        if self.redis:
            await self.redis.close()

    async def get(self, key: str) -> Optional[dict]:
        """
        Retrieve a value from the Redis cache.

        Args:
            key (str): The key to retrieve.

        Returns:
            Optional[dict]: The value associated with the key, or None if not found.
        """
        data = await self.redis.get(key)
        if data:
            return orjson.loads(data)
        return None

    async def set(self, key: str, value: dict, ttl: int = settings.ttl_cache) -> None:
        """
        Store a value in the Redis cache.

        Args:
            key (str): The key to store.
            value (dict): The value to store.
            ttl (int, optional): Time to live in seconds. Defaults to 120.
        """
        await self.redis.set(key, orjson.dumps(value), ex=ttl)
