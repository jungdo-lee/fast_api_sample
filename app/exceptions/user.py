from app.exceptions.base import AppException


class UserNotFoundError(AppException):
    def __init__(self) -> None:
        super().__init__(
            status_code=404,
            error_code="USER_001",
            message="사용자를 찾을 수 없습니다",
        )


class EmailAlreadyExistsError(AppException):
    def __init__(self) -> None:
        super().__init__(
            status_code=409,
            error_code="USER_002",
            message="이미 사용 중인 이메일입니다",
        )


class InvalidPasswordFormatError(AppException):
    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            error_code="USER_003",
            message="비밀번호 형식이 올바르지 않습니다",
        )


class CurrentPasswordMismatchError(AppException):
    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            error_code="USER_004",
            message="현재 비밀번호가 일치하지 않습니다",
        )


class SamePasswordError(AppException):
    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            error_code="USER_005",
            message="새 비밀번호는 현재 비밀번호와 달라야 합니다",
        )


class AccountSuspendedError(AppException):
    def __init__(self) -> None:
        super().__init__(
            status_code=403,
            error_code="USER_006",
            message="정지된 계정입니다",
        )


class AccountWithdrawnError(AppException):
    def __init__(self) -> None:
        super().__init__(
            status_code=403,
            error_code="USER_007",
            message="탈퇴한 계정입니다",
        )


class DeviceRequiredError(AppException):
    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            error_code="DEVICE_001",
            message="디바이스 ID가 필요합니다",
        )


class DeviceNotFoundError(AppException):
    def __init__(self) -> None:
        super().__init__(
            status_code=404,
            error_code="DEVICE_002",
            message="등록되지 않은 디바이스입니다",
        )


class CannotLogoutCurrentDeviceError(AppException):
    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            error_code="DEVICE_003",
            message="현재 디바이스는 이 방법으로 로그아웃할 수 없습니다",
        )
