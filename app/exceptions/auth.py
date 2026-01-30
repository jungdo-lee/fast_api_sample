from app.exceptions.base import AppException


class InvalidCredentialsError(AppException):
    def __init__(self) -> None:
        super().__init__(
            status_code=401,
            error_code="AUTH_001",
            message="이메일 또는 비밀번호가 올바르지 않습니다",
        )


class TokenExpiredError(AppException):
    def __init__(self) -> None:
        super().__init__(
            status_code=401,
            error_code="AUTH_002",
            message="인증이 만료되었습니다. 다시 로그인해주세요",
        )


class InvalidTokenError(AppException):
    def __init__(self) -> None:
        super().__init__(
            status_code=401,
            error_code="AUTH_003",
            message="유효하지 않은 인증 정보입니다",
        )


class SessionExpiredError(AppException):
    def __init__(self) -> None:
        super().__init__(
            status_code=401,
            error_code="AUTH_004",
            message="세션이 만료되었습니다. 다시 로그인해주세요",
        )


class InvalidRefreshTokenError(AppException):
    def __init__(self) -> None:
        super().__init__(
            status_code=401,
            error_code="AUTH_005",
            message="유효하지 않은 갱신 토큰입니다",
        )


class TokenRevokedError(AppException):
    def __init__(self) -> None:
        super().__init__(
            status_code=401,
            error_code="AUTH_006",
            message="로그아웃된 세션입니다",
        )


class DeviceMismatchError(AppException):
    def __init__(self) -> None:
        super().__init__(
            status_code=401,
            error_code="AUTH_007",
            message="다른 기기에서 발급된 인증 정보입니다",
        )


class ForbiddenError(AppException):
    def __init__(self) -> None:
        super().__init__(
            status_code=403,
            error_code="AUTH_008",
            message="접근 권한이 없습니다",
        )


class TooManyLoginAttemptsError(AppException):
    def __init__(self) -> None:
        super().__init__(
            status_code=429,
            error_code="AUTH_009",
            message="로그인 시도가 너무 많습니다. 잠시 후 다시 시도해주세요",
        )
