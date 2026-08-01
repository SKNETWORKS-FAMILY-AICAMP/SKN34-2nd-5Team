"""Public request and response contracts for React and the demo UI."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


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


class RoleUpdateRequest(DecisionRequest):
    access_role: Literal["VIEWER", "OPERATOR"]


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
    is_admin: bool
    created_at: datetime
    approved_at: datetime | None


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
