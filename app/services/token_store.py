import json
from datetime import datetime, timezone

import redis.asyncio as aioredis
import structlog

logger = structlog.get_logger("app.services.token_store")


class TokenStore:
    def __init__(self, redis: aioredis.Redis) -> None:
        self.redis = redis

    # --- Refresh Token Storage ---

    async def store_refresh_token(
        self,
        user_id: str,
        device_id: str,
        token_id: str,
        device_name: str | None,
        os_type: str | None,
        app_version: str | None,
        ip_address: str | None,
        expires_at: datetime,
    ) -> None:
        key = f"auth:rt:{user_id}:{device_id}"
        now = datetime.now(timezone.utc)
        ttl = int((expires_at - now).total_seconds())
        if ttl <= 0:
            return

        data = {
            "token_id": token_id,
            "user_id": user_id,
            "device_id": device_id,
            "device_name": device_name,
            "os_type": os_type,
            "app_version": app_version,
            "ip_address": ip_address,
            "issued_at": int(now.timestamp()),
            "expires_at": int(expires_at.timestamp()),
        }

        await self.redis.setex(key, ttl, json.dumps(data))
        await self.redis.sadd(f"auth:devices:{user_id}", device_id)

        await logger.ainfo(
            "Refresh token stored",
            user_id=user_id,
            device_id=device_id,
        )

    async def get_refresh_token(
        self, user_id: str, device_id: str
    ) -> dict | None:
        key = f"auth:rt:{user_id}:{device_id}"
        data = await self.redis.get(key)
        if data is None:
            return None
        return json.loads(data)

    async def delete_refresh_token(self, user_id: str, device_id: str) -> None:
        key = f"auth:rt:{user_id}:{device_id}"
        await self.redis.delete(key)
        await self.redis.srem(f"auth:devices:{user_id}", device_id)

    async def delete_all_refresh_tokens(self, user_id: str) -> int:
        device_ids = await self.redis.smembers(f"auth:devices:{user_id}")
        count = len(device_ids)
        if count > 0:
            pipe = self.redis.pipeline()
            for device_id in device_ids:
                pipe.delete(f"auth:rt:{user_id}:{device_id}")
            pipe.delete(f"auth:devices:{user_id}")
            await pipe.execute()
        else:
            await self.redis.delete(f"auth:devices:{user_id}")
        return count

    async def get_active_device_ids(self, user_id: str) -> set[str]:
        return await self.redis.smembers(f"auth:devices:{user_id}")

    # --- Blacklist ---

    async def blacklist_token(
        self,
        jti: str,
        user_id: str,
        device_id: str,
        reason: str,
        ttl_seconds: int,
    ) -> None:
        if ttl_seconds <= 0:
            return

        key = f"auth:blacklist:{jti}"
        data = {
            "user_id": user_id,
            "device_id": device_id,
            "reason": reason,
            "revoked_at": int(datetime.now(timezone.utc).timestamp()),
        }
        await self.redis.setex(key, ttl_seconds, json.dumps(data))

    async def is_token_blacklisted(self, jti: str) -> bool:
        return await self.redis.exists(f"auth:blacklist:{jti}") > 0
