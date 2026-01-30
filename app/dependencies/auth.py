from dataclasses import dataclass
from datetime import datetime

import redis.asyncio as aioredis
from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.dependencies.redis import get_redis
from app.exceptions.auth import DeviceMismatchError, TokenRevokedError
from app.services.jwt import AccessTokenPayload, JWTService, get_jwt_service
from app.services.token_store import TokenStore

security = HTTPBearer()


@dataclass
class CurrentUser:
    user_id: str
    email: str
    name: str
    device_id: str
    token_jti: str
    token_exp: datetime


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    x_device_id: str = Header(..., alias="X-Device-Id"),
    redis: aioredis.Redis = Depends(get_redis),
    jwt_service: JWTService = Depends(get_jwt_service),
) -> CurrentUser:
    token = credentials.credentials

    payload: AccessTokenPayload = jwt_service.decode_access_token(token)

    if payload.device_id != x_device_id:
        raise DeviceMismatchError()

    token_store = TokenStore(redis)
    if await token_store.is_token_blacklisted(payload.jti):
        raise TokenRevokedError()

    return CurrentUser(
        user_id=payload.sub,
        email=payload.email,
        name=payload.name,
        device_id=payload.device_id,
        token_jti=payload.jti,
        token_exp=payload.exp,
    )
