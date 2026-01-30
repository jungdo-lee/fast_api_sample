import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.dependencies.auth import CurrentUser, get_current_user
from app.dependencies.database import get_db
from app.dependencies.redis import get_redis
from app.repositories.login_history import LoginHistoryRepository
from app.repositories.user import UserRepository
from app.repositories.user_device import UserDeviceRepository
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    LogoutAllResponse,
    RefreshRequest,
    SignupRequest,
    SignupResponse,
    TokenResponse,
)
from app.schemas.common import APIResponse, MessageResponse
from app.services.auth import AuthService
from app.services.jwt import JWTService, get_jwt_service
from app.services.token_store import TokenStore

settings = get_settings()

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _get_auth_service(
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
    jwt_service: JWTService = Depends(get_jwt_service),
) -> AuthService:
    return AuthService(
        user_repo=UserRepository(db),
        device_repo=UserDeviceRepository(db),
        history_repo=LoginHistoryRepository(db),
        jwt_service=jwt_service,
        token_store=TokenStore(redis),
    )


@router.post("/signup", response_model=APIResponse[SignupResponse], status_code=201)
@limiter.limit(settings.rate_limit_signup)
async def signup(
    body: SignupRequest,
    request: Request,
    service: AuthService = Depends(_get_auth_service),
) -> APIResponse[SignupResponse]:
    result = await service.signup(
        email=body.email,
        password=body.password,
        name=body.name,
        phone_number=body.phone_number,
        marketing_agreed=body.marketing_agreed,
    )
    trace_id = getattr(request.state, "request_id", None)
    return APIResponse(success=True, data=result, trace_id=trace_id)


@router.post("/login", response_model=APIResponse[LoginResponse])
@limiter.limit(settings.rate_limit_login)
async def login(
    body: LoginRequest,
    request: Request,
    x_device_id: str = Header(..., alias="X-Device-Id"),
    x_device_name: str | None = Header(None, alias="X-Device-Name"),
    x_app_version: str | None = Header(None, alias="X-App-Version"),
    x_os_type: str = Header("unknown", alias="X-OS-Type"),
    x_os_version: str | None = Header(None, alias="X-OS-Version"),
    service: AuthService = Depends(_get_auth_service),
) -> APIResponse[LoginResponse]:
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    result = await service.login(
        email=body.email,
        password=body.password,
        device_id=x_device_id,
        device_name=x_device_name,
        os_type=x_os_type,
        os_version=x_os_version,
        app_version=x_app_version,
        ip_address=client_ip,
        user_agent=user_agent,
    )
    trace_id = getattr(request.state, "request_id", None)
    return APIResponse(success=True, data=result, trace_id=trace_id)


@router.post("/refresh", response_model=APIResponse[TokenResponse])
@limiter.limit(settings.rate_limit_refresh)
async def refresh(
    body: RefreshRequest,
    request: Request,
    x_device_id: str = Header(..., alias="X-Device-Id"),
    x_device_name: str | None = Header(None, alias="X-Device-Name"),
    x_app_version: str | None = Header(None, alias="X-App-Version"),
    x_os_type: str | None = Header(None, alias="X-OS-Type"),
    service: AuthService = Depends(_get_auth_service),
) -> APIResponse[TokenResponse]:
    client_ip = request.client.host if request.client else None

    result = await service.refresh(
        refresh_token_str=body.refresh_token,
        device_id=x_device_id,
        device_name=x_device_name,
        os_type=x_os_type,
        app_version=x_app_version,
        ip_address=client_ip,
    )
    trace_id = getattr(request.state, "request_id", None)
    return APIResponse(success=True, data=result, trace_id=trace_id)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: AuthService = Depends(_get_auth_service),
) -> MessageResponse:
    await service.logout(
        user_id=current_user.user_id,
        device_id=current_user.device_id,
        access_token_jti=current_user.token_jti,
        access_token_exp=current_user.token_exp,
    )
    trace_id = getattr(request.state, "request_id", None)
    return MessageResponse(
        message="Successfully logged out",
        trace_id=trace_id,
    )


@router.post("/logout/all", response_model=APIResponse[LogoutAllResponse])
async def logout_all(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: AuthService = Depends(_get_auth_service),
) -> APIResponse[LogoutAllResponse]:
    count = await service.logout_all(
        user_id=current_user.user_id,
        access_token_jti=current_user.token_jti,
        access_token_exp=current_user.token_exp,
    )
    trace_id = getattr(request.state, "request_id", None)
    return APIResponse(
        success=True,
        data=LogoutAllResponse(logged_out_devices=count),
        message="Successfully logged out from all devices",
        trace_id=trace_id,
    )
