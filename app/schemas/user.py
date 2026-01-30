import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.validators import validate_password_strength


class UserResponse(BaseModel):
    user_id: str
    email: str
    name: str
    phone_number: str | None = None
    profile_image_url: str | None = None
    marketing_agreed: bool
    created_at: datetime
    updated_at: datetime


class UserUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    phone_number: str | None = Field(default=None, max_length=20)

    @model_validator(mode="after")
    def check_at_least_one_field(self) -> "UserUpdateRequest":
        if self.name is None and self.phone_number is None:
            raise ValueError("At least one field must be provided")
        return self

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: str | None) -> str | None:
        if v is not None and not re.match(r"^01[016789]\d{7,8}$", v):
            raise ValueError("Invalid phone number format")
        return v


class UserUpdateResponse(BaseModel):
    user_id: str
    name: str
    phone_number: str | None = None
    updated_at: datetime


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_strength(v)


class AccountDeleteRequest(BaseModel):
    password: str
    reason: str | None = None
