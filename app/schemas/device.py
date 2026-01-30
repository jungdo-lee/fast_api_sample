from datetime import datetime

from pydantic import BaseModel


class DeviceResponse(BaseModel):
    device_id: str
    device_name: str | None = None
    os_type: str
    os_version: str | None = None
    app_version: str | None = None
    last_login_at: datetime | None = None
    last_access_at: datetime | None = None
    ip_address: str | None = None
    is_current: bool = False


class DeviceHeaders(BaseModel):
    device_id: str
    device_name: str | None = None
    app_version: str | None = None
    os_type: str | None = None
    os_version: str | None = None
