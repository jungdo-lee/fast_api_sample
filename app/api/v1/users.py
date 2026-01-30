import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import CurrentUser, get_current_user
from app.dependencies.database import get_db
from app.dependencies.redis import get_redis
from app.repositories.user import UserRepository
from app.repositories.user_device import UserDeviceRepository
from app.schemas.common import APIResponse, MessageResponse
from app.schemas.user import (
    AccountDeleteRequest,
    PasswordChangeRequest,
    UserResponse,
    UserUpdateRequest,
    UserUpdateResponse,
)
from app.services.token_store import TokenStore
from app.services.user import UserService

router = APIRouter(prefix="/users", tags=["Users"])


def _get_user_service(
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> UserService:
    return UserService(
        user_repo=UserRepository(db),
        device_repo=UserDeviceRepository(db),
        token_store=TokenStore(redis),
    )


@router.get("/me", response_model=APIResponse[UserResponse])
async def get_me(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: UserService = Depends(_get_user_service),
) -> APIResponse[UserResponse]:
    result = await service.get_me(current_user.user_id)
    trace_id = getattr(request.state, "request_id", None)
    return APIResponse(success=True, data=result, trace_id=trace_id)


@router.patch("/me", response_model=APIResponse[UserUpdateResponse])
async def update_me(
    body: UserUpdateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: UserService = Depends(_get_user_service),
) -> APIResponse[UserUpdateResponse]:
    result = await service.update_me(
        user_id=current_user.user_id,
        name=body.name,
        phone_number=body.phone_number,
    )
    trace_id = getattr(request.state, "request_id", None)
    return APIResponse(success=True, data=result, trace_id=trace_id)


@router.put("/me/password", response_model=MessageResponse)
async def change_password(
    body: PasswordChangeRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: UserService = Depends(_get_user_service),
) -> MessageResponse:
    await service.change_password(
        user_id=current_user.user_id,
        current_password=body.current_password,
        new_password=body.new_password,
    )
    trace_id = getattr(request.state, "request_id", None)
    return MessageResponse(
        message="Password changed successfully. Please login again.",
        trace_id=trace_id,
    )


@router.delete("/me", response_model=MessageResponse)
async def delete_account(
    body: AccountDeleteRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: UserService = Depends(_get_user_service),
) -> MessageResponse:
    await service.delete_account(
        user_id=current_user.user_id,
        password=body.password,
    )
    trace_id = getattr(request.state, "request_id", None)
    return MessageResponse(
        message="Account deleted successfully",
        trace_id=trace_id,
    )
