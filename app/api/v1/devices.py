import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import CurrentUser, get_current_user
from app.dependencies.database import get_db
from app.dependencies.redis import get_redis
from app.repositories.user_device import UserDeviceRepository
from app.schemas.common import APIResponse, MessageResponse
from app.schemas.device import DeviceResponse
from app.services.device import DeviceService
from app.services.token_store import TokenStore

router = APIRouter(prefix="/users/me/devices", tags=["Devices"])


def _get_device_service(
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> DeviceService:
    return DeviceService(
        device_repo=UserDeviceRepository(db),
        token_store=TokenStore(redis),
    )


@router.get("", response_model=APIResponse[list[DeviceResponse]])
async def list_devices(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: DeviceService = Depends(_get_device_service),
) -> APIResponse[list[DeviceResponse]]:
    result = await service.get_devices(
        user_id=current_user.user_id,
        current_device_id=current_user.device_id,
    )
    trace_id = getattr(request.state, "request_id", None)
    return APIResponse(success=True, data=result, trace_id=trace_id)


@router.delete("/{device_id}", response_model=MessageResponse)
async def force_logout_device(
    device_id: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: DeviceService = Depends(_get_device_service),
) -> MessageResponse:
    await service.force_logout_device(
        user_id=current_user.user_id,
        target_device_id=device_id,
        current_device_id=current_user.device_id,
    )
    trace_id = getattr(request.state, "request_id", None)
    return MessageResponse(
        message="Device logged out successfully",
        trace_id=trace_id,
    )
