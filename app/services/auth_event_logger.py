import structlog

logger = structlog.get_logger("app.auth.events")


class AuthEventLogger:
    @staticmethod
    async def log_login_success(user_id: str, device_id: str, ip_address: str) -> None:
        await logger.ainfo(
            "LOGIN_SUCCESS",
            event_type="LOGIN_SUCCESS",
            user_id=user_id,
            device_id=device_id,
            client_ip=ip_address,
        )

    @staticmethod
    async def log_login_failure(
        email: str, device_id: str, ip_address: str, reason: str
    ) -> None:
        await logger.awarning(
            "LOGIN_FAILURE",
            event_type="LOGIN_FAILURE",
            email=email,
            device_id=device_id,
            client_ip=ip_address,
            failure_reason=reason,
        )

    @staticmethod
    async def log_logout(user_id: str, device_id: str, logout_type: str) -> None:
        await logger.ainfo(
            "LOGOUT",
            event_type="LOGOUT",
            user_id=user_id,
            device_id=device_id,
            logout_type=logout_type,
        )

    @staticmethod
    async def log_token_refresh(user_id: str, device_id: str) -> None:
        await logger.ainfo(
            "TOKEN_REFRESH",
            event_type="TOKEN_REFRESH",
            user_id=user_id,
            device_id=device_id,
        )

    @staticmethod
    async def log_suspicious_activity(
        user_id: str | None, device_id: str, ip_address: str, activity: str
    ) -> None:
        await logger.awarning(
            "SUSPICIOUS_ACTIVITY",
            event_type="SUSPICIOUS_ACTIVITY",
            user_id=user_id,
            device_id=device_id,
            client_ip=ip_address,
            suspicious_activity=activity,
        )
