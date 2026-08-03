"""Public request and response contracts for React and the demo UI."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=100)
    organization: str = Field(default="", max_length=120)
    requested_role: str = Field(default="운영 담당자", max_length=80)
    signup_reason: str = Field(default="", max_length=500)

    @field_validator("full_name", "organization", "requested_role", "signup_reason")
    @classmethod
    def trim_text(cls, value: str) -> str:
        return value.strip()


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("identifier")
    @classmethod
    def trim_identifier(cls, value: str) -> str:
        return value.strip()


class DecisionRequest(BaseModel):
    note: str = Field(default="", max_length=500)

    @field_validator("note")
    @classmethod
    def trim_note(cls, value: str) -> str:
        return value.strip()


class ApprovalRequest(DecisionRequest):
    access_role: Literal["VIEWER", "OPERATOR"]
    region_code: str | None = Field(default=None, max_length=16)

    @field_validator("region_code")
    @classmethod
    def normalize_region(cls, value: str | None) -> str | None:
        return value.strip().upper() if value and value.strip() else None

    @model_validator(mode="after")
    def operator_requires_region(self):
        if self.access_role == "OPERATOR" and not self.region_code:
            raise ValueError("운영자 계정에는 담당 권역이 필요합니다.")
        return self


class RoleUpdateRequest(DecisionRequest):
    access_role: Literal["VIEWER", "OPERATOR"]
    region_code: str | None = Field(default=None, max_length=16)

    @field_validator("region_code")
    @classmethod
    def normalize_region(cls, value: str | None) -> str | None:
        return value.strip().upper() if value and value.strip() else None


class AdminUserCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    email: EmailStr | None = None
    password: str = Field(min_length=10, max_length=128)
    full_name: str = Field(min_length=2, max_length=100)
    access_role: Literal["VIEWER", "OPERATOR"]
    region_code: str | None = Field(default=None, max_length=16)
    must_change_password: bool = True

    @field_validator("username", "full_name")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("region_code")
    @classmethod
    def normalize_region(cls, value: str | None) -> str | None:
        return value.strip().upper() if value and value.strip() else None

    @model_validator(mode="after")
    def operator_requires_region(self):
        if self.access_role == "OPERATOR" and not self.region_code:
            raise ValueError("운영자 계정에는 담당 권역이 필요합니다.")
        return self


class AdminBulkRegionUsersRequest(BaseModel):
    region_codes: list[str] = Field(min_length=1, max_length=14)
    password_length: int = Field(default=14, ge=12, le=32)
    must_change_password: bool = True

    @field_validator("region_codes")
    @classmethod
    def normalize_regions(cls, values: list[str]) -> list[str]:
        normalized = [value.strip().upper() for value in values if value.strip()]
        if len(normalized) != len(set(normalized)):
            raise ValueError("권역 코드가 중복되었습니다.")
        return normalized


class AdminUserStatusRequest(DecisionRequest):
    active: bool


class PasswordResetRequest(DecisionRequest):
    new_password: str = Field(min_length=10, max_length=128)


class CreatedCredential(BaseModel):
    user: "UserResponse"
    temporary_password: str


class BulkUserCreateResponse(BaseModel):
    items: list[CreatedCredential]
    total: int


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str | None
    email: EmailStr
    full_name: str
    organization: str
    requested_role: str
    signup_reason: str
    status: Literal["PENDING", "APPROVED", "REJECTED", "SUSPENDED"]
    access_role: Literal["VIEWER", "OPERATOR", "ADMIN"] | None
    region_code: str | None
    must_change_password: bool
    is_admin: bool
    created_at: datetime
    approved_at: datetime | None
    last_login_at: datetime | None


class RegistrationResponse(BaseModel):
    message: str
    user: UserResponse


class LoginResponse(BaseModel):
    message: str
    user: UserResponse
    redirect_to: str


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int


class MessageResponse(BaseModel):
    message: str
