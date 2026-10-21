"""Схемы авторизации и рабочего пространства."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=256)
    display_name: str = Field(default="", max_length=120)
    workspace_name: str = Field(default="Моё рабочее пространство", max_length=120)

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if "@" not in cleaned or "." not in cleaned.split("@")[-1]:
            raise ValueError("Укажите корректный адрес электронной почты")
        return cleaned

    @field_validator("display_name", "workspace_name")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class WorkspaceOut(BaseModel):
    id: str
    name: str
    slug: str
    is_demo: bool


class UserOut(BaseModel):
    id: str
    email: str
    display_name: str
    role: str
    workspace: WorkspaceOut


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut
