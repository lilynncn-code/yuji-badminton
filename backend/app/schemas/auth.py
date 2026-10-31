from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


def strip_text(value: str) -> str:
    if value is None:
        return ""
    return str(value).strip()


class RegisterRequest(BaseModel):
    username: str = ""
    phone: str = ""
    password: str = ""
    name: Optional[str] = Field(default=None, max_length=50)
    sms_code: str = ""

    @field_validator("username", "phone", "name", "sms_code", mode="before")
    @classmethod
    def trim_text_fields(cls, value: str) -> str:
        return strip_text(value)


class LoginRequest(BaseModel):
    account: str = ""
    password: str = ""

    @field_validator("account", mode="before")
    @classmethod
    def trim_account(cls, value: str) -> str:
        return strip_text(value)


class ForgotPasswordRequest(BaseModel):
    account: str = ""
    phone: str = ""
    new_password: str = ""
    sms_code: str = ""

    @field_validator("account", "phone", "sms_code", mode="before")
    @classmethod
    def trim_text_fields(cls, value: str) -> str:
        return strip_text(value)


class ChangePasswordRequest(BaseModel):
    old_password: str = ""
    new_password: str = ""
    confirm_password: str = ""


class PhoneChangeStartRequest(BaseModel):
    password: str = Field(min_length=1,max_length=50)
    new_phone: str = Field(min_length=11,max_length=11,pattern=r'^1[3-9]\d{9}$')
    old_code: str = Field(min_length=6,max_length=6,pattern=r'^\d{6}$')


class PhoneChangeTicketRequest(BaseModel):
    change_id: str = Field(min_length=32,max_length=100,pattern=r'^[A-Za-z0-9_-]+$')


class PhoneChangeFinishRequest(PhoneChangeTicketRequest):
    new_code: str = Field(min_length=6,max_length=6,pattern=r'^\d{6}$')


class SendSmsRequest(BaseModel):
    phone: str = ""
    scene: str = ""

    @field_validator("phone", "scene", mode="before")
    @classmethod
    def trim_text_fields(cls, value: str) -> str:
        return strip_text(value)


class MessageResponse(BaseModel):
    message: str


class UserResponse(BaseModel):
    id: int
    username: str
    phone: str
    name: str
    cover: str = ""
    club: str = ""
    hand: str = "右手持拍"
    avatar: str
    city: str
    level_tag: str
    bio: str = ''

    model_config = ConfigDict(from_attributes=True)


class AuthResponse(BaseModel):
    token: str
    user: UserResponse
    message: str
