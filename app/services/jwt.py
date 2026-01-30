from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import uuid

import jwt

from app.core.config import get_settings

settings = get_settings()


@dataclass
class AccessTokenPayload:
    sub: str
    email: str
    name: str
    device_id: str
    jti: str
    exp: datetime
    iat: datetime


@dataclass
class RefreshTokenPayload:
    sub: str
    device_id: str
    jti: str
    exp: datetime
    iat: datetime


class JWTService:
    def __init__(self) -> None:
        self._private_key: str | None = None
        self._public_key: str | None = None

    @property
    def private_key(self) -> str:
        if self._private_key is None:
            self._private_key = settings.jwt_private_key_path.read_text()
        return self._private_key

    @property
    def public_key(self) -> str:
        if self._public_key is None:
            self._public_key = settings.jwt_public_key_path.read_text()
        return self._public_key

    def create_access_token(
        self,
        user_id: str,
        email: str,
        name: str,
        device_id: str,
    ) -> tuple[str, str, datetime]:
        now = datetime.now(timezone.utc)
        exp = now + timedelta(seconds=settings.jwt_access_token_expire_seconds)
        jti = str(uuid.uuid4())

        payload = {
            "iss": settings.jwt_issuer,
            "sub": user_id,
            "aud": settings.jwt_audience,
            "iat": now,
            "exp": exp,
            "jti": jti,
            "type": "access",
            "device_id": device_id,
            "email": email,
            "name": name,
        }

        token = jwt.encode(payload, self.private_key, algorithm=settings.jwt_algorithm)
        return token, jti, exp

    def create_refresh_token(
        self,
        user_id: str,
        device_id: str,
    ) -> tuple[str, str, datetime]:
        now = datetime.now(timezone.utc)
        exp = now + timedelta(seconds=settings.jwt_refresh_token_expire_seconds)
        jti = str(uuid.uuid4())

        payload = {
            "iss": settings.jwt_issuer,
            "sub": user_id,
            "iat": now,
            "exp": exp,
            "jti": jti,
            "type": "refresh",
            "device_id": device_id,
        }

        token = jwt.encode(payload, self.private_key, algorithm=settings.jwt_algorithm)
        return token, jti, exp

    def decode_access_token(self, token: str) -> AccessTokenPayload:
        try:
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[settings.jwt_algorithm],
                issuer=settings.jwt_issuer,
                audience=settings.jwt_audience,
            )
        except jwt.ExpiredSignatureError:
            from app.exceptions.auth import TokenExpiredError
            raise TokenExpiredError()
        except jwt.InvalidTokenError:
            from app.exceptions.auth import InvalidTokenError
            raise InvalidTokenError()

        if payload.get("type") != "access":
            from app.exceptions.auth import InvalidTokenError
            raise InvalidTokenError()

        return AccessTokenPayload(
            sub=payload["sub"],
            email=payload["email"],
            name=payload["name"],
            device_id=payload["device_id"],
            jti=payload["jti"],
            exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
        )

    def decode_refresh_token(self, token: str) -> RefreshTokenPayload:
        try:
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[settings.jwt_algorithm],
                issuer=settings.jwt_issuer,
                options={"verify_aud": False},
            )
        except jwt.ExpiredSignatureError:
            from app.exceptions.auth import SessionExpiredError
            raise SessionExpiredError()
        except jwt.InvalidTokenError:
            from app.exceptions.auth import InvalidRefreshTokenError
            raise InvalidRefreshTokenError()

        if payload.get("type") != "refresh":
            from app.exceptions.auth import InvalidRefreshTokenError
            raise InvalidRefreshTokenError()

        return RefreshTokenPayload(
            sub=payload["sub"],
            device_id=payload["device_id"],
            jti=payload["jti"],
            exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
        )

    def validate_keys(self) -> None:
        """Validate JWT key files exist and are readable at startup."""
        if not settings.jwt_private_key_path.exists():
            raise FileNotFoundError(
                f"JWT private key not found: {settings.jwt_private_key_path}"
            )
        if not settings.jwt_public_key_path.exists():
            raise FileNotFoundError(
                f"JWT public key not found: {settings.jwt_public_key_path}"
            )
        # Force load keys to validate they're readable
        _ = self.private_key
        _ = self.public_key


_jwt_service: JWTService | None = None


def get_jwt_service() -> JWTService:
    global _jwt_service
    if _jwt_service is None:
        _jwt_service = JWTService()
    return _jwt_service
