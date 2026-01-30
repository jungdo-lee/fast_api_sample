import pytest

from app.services.jwt import JWTService


@pytest.fixture
def jwt_service() -> JWTService:
    return JWTService()


def test_create_and_decode_access_token(jwt_service: JWTService):
    token, jti, exp = jwt_service.create_access_token(
        user_id="test-user-id",
        email="test@example.com",
        name="Test User",
        device_id="test-device-id",
    )
    assert token
    assert jti
    assert exp

    payload = jwt_service.decode_access_token(token)
    assert payload.sub == "test-user-id"
    assert payload.email == "test@example.com"
    assert payload.name == "Test User"
    assert payload.device_id == "test-device-id"
    assert payload.jti == jti


def test_create_and_decode_refresh_token(jwt_service: JWTService):
    token, jti, exp = jwt_service.create_refresh_token(
        user_id="test-user-id",
        device_id="test-device-id",
    )
    assert token
    assert jti
    assert exp

    payload = jwt_service.decode_refresh_token(token)
    assert payload.sub == "test-user-id"
    assert payload.device_id == "test-device-id"
    assert payload.jti == jti


def test_decode_invalid_token(jwt_service: JWTService):
    from app.exceptions.auth import InvalidTokenError

    with pytest.raises(InvalidTokenError):
        jwt_service.decode_access_token("invalid.token.here")


def test_decode_refresh_as_access_raises_error(jwt_service: JWTService):
    from app.exceptions.auth import InvalidTokenError

    refresh_token, _, _ = jwt_service.create_refresh_token(
        user_id="test-user-id",
        device_id="test-device-id",
    )
    with pytest.raises(InvalidTokenError):
        jwt_service.decode_access_token(refresh_token)
