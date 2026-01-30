from app.exceptions.user import CannotLogoutCurrentDeviceError, DeviceNotFoundError
from app.repositories.user_device import UserDeviceRepository
from app.schemas.device import DeviceResponse
from app.services.auth_event_logger import AuthEventLogger
from app.services.token_store import TokenStore


class DeviceService:
    def __init__(
        self,
        device_repo: UserDeviceRepository,
        token_store: TokenStore,
    ) -> None:
        self.device_repo = device_repo
        self.token_store = token_store

    async def get_devices(
        self, user_id: str, current_device_id: str
    ) -> list[DeviceResponse]:
        devices = await self.device_repo.get_active_devices(user_id)
        return [
            DeviceResponse(
                device_id=d.device_id,
                device_name=d.device_name,
                os_type=d.os_type,
                os_version=d.os_version,
                app_version=d.app_version,
                last_login_at=d.last_login_at,
                last_access_at=d.last_access_at,
                ip_address=d.last_login_ip,
                is_current=(d.device_id == current_device_id),
            )
            for d in devices
        ]

    async def force_logout_device(
        self,
        user_id: str,
        target_device_id: str,
        current_device_id: str,
    ) -> None:
        if target_device_id == current_device_id:
            raise CannotLogoutCurrentDeviceError()

        device = await self.device_repo.get_by_user_and_device(user_id, target_device_id)
        if device is None or not device.is_active:
            raise DeviceNotFoundError()

        await self.token_store.delete_refresh_token(user_id, target_device_id)
        await self.device_repo.deactivate_device(user_id, target_device_id)

        await AuthEventLogger.log_logout(
            user_id=user_id,
            device_id=target_device_id,
            logout_type="FORCE",
        )
