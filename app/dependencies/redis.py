from collections.abc import AsyncGenerator

import redis.asyncio as aioredis

from app.core import redis as redis_module


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    if redis_module.redis_client is None:
        raise RuntimeError("Redis not initialized")
    yield redis_module.redis_client
