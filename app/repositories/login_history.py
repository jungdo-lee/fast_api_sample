from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.login_history import LoginHistory


class LoginHistoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        user_id: str | None,
        device_id: str,
        ip_address: str | None,
        user_agent: str | None,
        os_type: str | None,
        app_version: str | None,
        login_type: str = "EMAIL",
        success: bool = True,
        failure_reason: str | None = None,
    ) -> LoginHistory:
        history = LoginHistory(
            user_id=user_id,
            device_id=device_id,
            ip_address=ip_address,
            user_agent=user_agent,
            os_type=os_type,
            app_version=app_version,
            login_at=datetime.now(timezone.utc),
            login_type=login_type,
            success=success,
            failure_reason=failure_reason,
        )
        self.session.add(history)
        await self.session.flush()
        return history
