from datetime import datetime, timezone

import uuid

import structlog
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.core.security import hash_password, verify_password, DUMMY_HASH
from app.exceptions.auth import InvalidCredentialsError, InvalidRefreshTokenError
from app.exceptions.user import (
    AccountSuspendedError,
    AccountWithdrawnError,
    EmailAlreadyExistsError,
)
from app.models.user import User
from app.repositories.login_history import LoginHistoryRepository
from app.repositories.user import UserRepository
from app.repositories.user_device import UserDeviceRepository
from app.schemas.auth import LoginResponse, LoginUserInfo, SignupResponse, TokenResponse
from app.services.auth_event_logger import AuthEventLogger
from app.services.jwt import JWTService
from app.services.token_store import TokenStore

logger = structlog.get_logger("app.services.auth")
settings = get_settings()


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        device_repo: UserDeviceRepository,
        history_repo: LoginHistoryRepository,
        jwt_service: JWTService,
        token_store: TokenStore,
    ) -> None:
        self.user_repo = user_repo
        self.device_repo = device_repo
        self.history_repo = history_repo
        self.jwt_service = jwt_service
        self.token_store = token_store

    async def signup(
        self,
        email: str,
        password: str,
        name: str,
        phone_number: str | None,
        marketing_agreed: bool,
    ) -> SignupResponse:
        if await self.user_repo.email_exists(email):
            raise EmailAlreadyExistsError()

        now = datetime.now(timezone.utc)
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            hashed_password=hash_password(password),
            name=name,
            phone_number=phone_number,
            status="ACTIVE",
            marketing_agreed=marketing_agreed,
            created_at=now,
            updated_at=now,
        )

        try:
            await self.user_repo.create(user)
        except IntegrityError:
            raise EmailAlreadyExistsError()

        return SignupResponse(
            user_id=user.id,
            email=user.email,
            name=user.name,
            created_at=user.created_at,
        )

    async def login(
        self,
        email: str,
        password: str,
        device_id: str,
        device_name: str | None,
        os_type: str,
        os_version: str | None,
        app_version: str | None,
        ip_address: str | None,
        user_agent: str | None,
    ) -> LoginResponse:
        user = await self.user_repo.get_by_email(email)

        # Constant-time password verification to prevent timing attacks
        if user is None:
            verify_password(password, DUMMY_HASH)
            valid = False
        else:
            valid = verify_password(password, user.hashed_password)

        if not valid:
            await self.history_repo.create(
                user_id=user.id if user else None,
                device_id=device_id,
                ip_address=ip_address,
                user_agent=user_agent,
                os_type=os_type,
                app_version=app_version,
                success=False,
                failure_reason="INVALID_CREDENTIALS",
            )
            await AuthEventLogger.log_login_failure(
                email=email,
                device_id=device_id,
                ip_address=ip_address or "unknown",
                reason="INVALID_CREDENTIALS",
            )
            raise InvalidCredentialsError()

        if user.status == "INACTIVE":
            raise AccountSuspendedError()
        if user.status == "WITHDRAWN":
            raise AccountWithdrawnError()

        await self.device_repo.upsert_device(
            user_id=user.id,
            device_id=device_id,
            device_name=device_name,
            os_type=os_type,
            os_version=os_version,
            app_version=app_version,
            ip_address=ip_address,
        )

        await self.user_repo.update_last_login(user.id)

        access_token, at_jti, at_exp = self.jwt_service.create_access_token(
            user_id=user.id,
            email=user.email,
            name=user.name,
            device_id=device_id,
        )
        refresh_token, rt_jti, rt_exp = self.jwt_service.create_refresh_token(
            user_id=user.id,
            device_id=device_id,
        )

        await self.token_store.store_refresh_token(
            user_id=user.id,
            device_id=device_id,
            token_id=rt_jti,
            device_name=device_name,
            os_type=os_type,
            app_version=app_version,
            ip_address=ip_address,
            expires_at=rt_exp,
        )

        await self.history_repo.create(
            user_id=user.id,
            device_id=device_id,
            ip_address=ip_address,
            user_agent=user_agent,
            os_type=os_type,
            app_version=app_version,
            success=True,
        )

        await AuthEventLogger.log_login_success(
            user_id=user.id,
            device_id=device_id,
            ip_address=ip_address or "unknown",
        )

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=settings.jwt_access_token_expire_seconds,
            refresh_expires_in=settings.jwt_refresh_token_expire_seconds,
            user=LoginUserInfo(
                user_id=user.id,
                email=user.email,
                name=user.name,
            ),
        )

    async def refresh(
        self,
        refresh_token_str: str,
        device_id: str,
        device_name: str | None,
        os_type: str | None,
        app_version: str | None,
        ip_address: str | None,
    ) -> TokenResponse:
        rt_payload = self.jwt_service.decode_refresh_token(refresh_token_str)

        if rt_payload.device_id != device_id:
            await AuthEventLogger.log_suspicious_activity(
                user_id=rt_payload.sub,
                device_id=device_id,
                ip_address=ip_address or "unknown",
                activity="REFRESH_DEVICE_MISMATCH",
            )
            raise InvalidRefreshTokenError()

        stored = await self.token_store.get_refresh_token(rt_payload.sub, device_id)
        if stored is None:
            raise InvalidRefreshTokenError()

        if stored["token_id"] != rt_payload.jti:
            await AuthEventLogger.log_suspicious_activity(
                user_id=rt_payload.sub,
                device_id=device_id,
                ip_address=ip_address or "unknown",
                activity="REFRESH_TOKEN_REUSE_ATTEMPT",
            )
            await self.token_store.delete_refresh_token(rt_payload.sub, device_id)
            raise InvalidRefreshTokenError()

        user = await self.user_repo.get_by_id(rt_payload.sub)
        if user is None:
            raise InvalidRefreshTokenError()

        access_token, _, _ = self.jwt_service.create_access_token(
            user_id=user.id,
            email=user.email,
            name=user.name,
            device_id=device_id,
        )
        new_refresh_token, new_rt_jti, new_rt_exp = self.jwt_service.create_refresh_token(
            user_id=user.id,
            device_id=device_id,
        )

        await self.token_store.store_refresh_token(
            user_id=user.id,
            device_id=device_id,
            token_id=new_rt_jti,
            device_name=device_name,
            os_type=os_type,
            app_version=app_version,
            ip_address=ip_address,
            expires_at=new_rt_exp,
        )

        await AuthEventLogger.log_token_refresh(
            user_id=user.id,
            device_id=device_id,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="Bearer",
            expires_in=settings.jwt_access_token_expire_seconds,
            refresh_expires_in=settings.jwt_refresh_token_expire_seconds,
        )

    async def logout(
        self,
        user_id: str,
        device_id: str,
        access_token_jti: str,
        access_token_exp: datetime,
    ) -> None:
        now = datetime.now(timezone.utc)
        ttl = int((access_token_exp - now).total_seconds())

        await self.token_store.blacklist_token(
            jti=access_token_jti,
            user_id=user_id,
            device_id=device_id,
            reason="logout",
            ttl_seconds=ttl,
        )
        await self.token_store.delete_refresh_token(user_id, device_id)
        await self.device_repo.deactivate_device(user_id, device_id)

        await AuthEventLogger.log_logout(
            user_id=user_id,
            device_id=device_id,
            logout_type="SELF",
        )

    async def logout_all(
        self,
        user_id: str,
        access_token_jti: str,
        access_token_exp: datetime,
    ) -> int:
        now = datetime.now(timezone.utc)
        ttl = int((access_token_exp - now).total_seconds())

        await self.token_store.blacklist_token(
            jti=access_token_jti,
            user_id=user_id,
            device_id="all",
            reason="logout_all",
            ttl_seconds=ttl,
        )

        count = await self.token_store.delete_all_refresh_tokens(user_id)
        await self.device_repo.deactivate_all_devices(user_id)

        await AuthEventLogger.log_logout(
            user_id=user_id,
            device_id="all",
            logout_type="ALL_DEVICES",
        )

        return count
