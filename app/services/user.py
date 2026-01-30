from datetime import datetime, timezone

from app.core.security import hash_password, verify_password
from app.exceptions.user import (
    CurrentPasswordMismatchError,
    SamePasswordError,
    UserNotFoundError,
)
from app.repositories.user import UserRepository
from app.repositories.user_device import UserDeviceRepository
from app.schemas.user import UserResponse, UserUpdateResponse
from app.services.token_store import TokenStore


class UserService:
    def __init__(
        self,
        user_repo: UserRepository,
        device_repo: UserDeviceRepository,
        token_store: TokenStore,
    ) -> None:
        self.user_repo = user_repo
        self.device_repo = device_repo
        self.token_store = token_store

    async def get_me(self, user_id: str) -> UserResponse:
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError()

        return UserResponse(
            user_id=user.id,
            email=user.email,
            name=user.name,
            phone_number=user.phone_number,
            profile_image_url=user.profile_image_url,
            marketing_agreed=user.marketing_agreed,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    async def update_me(
        self,
        user_id: str,
        name: str | None = None,
        phone_number: str | None = None,
    ) -> UserUpdateResponse:
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError()

        if name is not None:
            user.name = name
        if phone_number is not None:
            user.phone_number = phone_number
        user.updated_at = datetime.now(timezone.utc)

        await self.user_repo.update(user)

        return UserUpdateResponse(
            user_id=user.id,
            name=user.name,
            phone_number=user.phone_number,
            updated_at=user.updated_at,
        )

    async def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str,
    ) -> None:
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError()

        if not verify_password(current_password, user.hashed_password):
            raise CurrentPasswordMismatchError()

        if verify_password(new_password, user.hashed_password):
            raise SamePasswordError()

        user.hashed_password = hash_password(new_password)
        user.updated_at = datetime.now(timezone.utc)
        await self.user_repo.update(user)

        await self.token_store.delete_all_refresh_tokens(user_id)
        await self.device_repo.deactivate_all_devices(user_id)

    async def delete_account(
        self,
        user_id: str,
        password: str,
    ) -> None:
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError()

        if not verify_password(password, user.hashed_password):
            raise CurrentPasswordMismatchError()

        await self.user_repo.soft_delete(user)
        await self.token_store.delete_all_refresh_tokens(user_id)
        await self.device_repo.deactivate_all_devices(user_id)
