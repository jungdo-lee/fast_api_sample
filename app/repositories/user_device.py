from datetime import datetime, timezone

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_device import UserDevice


class UserDeviceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_user_and_device(
        self, user_id: str, device_id: str
    ) -> UserDevice | None:
        result = await self.session.execute(
            select(UserDevice).where(
                and_(
                    UserDevice.user_id == user_id,
                    UserDevice.device_id == device_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_active_devices(self, user_id: str) -> list[UserDevice]:
        result = await self.session.execute(
            select(UserDevice).where(
                and_(
                    UserDevice.user_id == user_id,
                    UserDevice.is_active == True,  # noqa: E712
                )
            )
        )
        return list(result.scalars().all())

    async def upsert_device(
        self,
        user_id: str,
        device_id: str,
        device_name: str | None,
        os_type: str,
        os_version: str | None,
        app_version: str | None,
        ip_address: str | None,
    ) -> UserDevice:
        device = await self.get_by_user_and_device(user_id, device_id)
        now = datetime.now(timezone.utc)

        if device is None:
            device = UserDevice(
                user_id=user_id,
                device_id=device_id,
                device_name=device_name,
                os_type=os_type,
                os_version=os_version,
                app_version=app_version,
                last_login_at=now,
                last_login_ip=ip_address,
                last_access_at=now,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            self.session.add(device)
        else:
            device.device_name = device_name or device.device_name
            device.os_type = os_type
            device.os_version = os_version or device.os_version
            device.app_version = app_version or device.app_version
            device.last_login_at = now
            device.last_login_ip = ip_address
            device.last_access_at = now
            device.is_active = True
            device.updated_at = now

        await self.session.flush()
        return device

    async def deactivate_device(self, user_id: str, device_id: str) -> bool:
        device = await self.get_by_user_and_device(user_id, device_id)
        if device is None:
            return False
        device.is_active = False
        device.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return True

    async def deactivate_all_devices(self, user_id: str) -> int:
        devices = await self.get_active_devices(user_id)
        now = datetime.now(timezone.utc)
        for device in devices:
            device.is_active = False
            device.updated_at = now
        await self.session.flush()
        return len(devices)
