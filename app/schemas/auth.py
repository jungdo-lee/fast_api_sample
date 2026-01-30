import re
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.validators import validate_password_strength


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    name: str = Field(min_length=1, max_length=100)
    phone_number: str | None = Field(default=None, max_length=20)
    marketing_agreed: bool = False

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_strength(v)

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: str | None) -> str | None:
        if v is not None and not re.match(r"^01[016789]\d{7,8}$", v):
            raise ValueError("Invalid phone number format")
        return v


class SignupResponse(BaseModel):
    user_id: str
    email: str
    name: str
    created_at: datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_expires_in: int


class LoginUserInfo(BaseModel):
    user_id: str
    email: str
    name: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_expires_in: int
    user: LoginUserInfo


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutAllResponse(BaseModel):
    logged_out_devices: int
