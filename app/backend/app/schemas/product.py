"""Схемы товара."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import Marketplace


def _strip(value: str) -> str:
    return (value or "").strip()


class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    category: str = Field(default="", max_length=255)
    marketplace: Marketplace = Marketplace.OTHER
    sku: str = Field(default="", max_length=120)
    description: str = Field(default="", max_length=20000)
    attributes: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def _check_name(cls, value: str) -> str:
        cleaned = _strip(value)
        if not cleaned:
            raise ValueError("Название товара обязательно")
        return cleaned

    @field_validator("category", "sku")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        return _strip(value)

    @field_validator("attributes")
    @classmethod
    def _limit_attributes(cls, value: Dict[str, Any]) -> Dict[str, Any]:
        if len(value) > 200:
            raise ValueError("Слишком много характеристик (максимум 200)")
        cleaned: Dict[str, Any] = {}
        for key, item in value.items():
            key_text = _strip(str(key))
            if not key_text:
                continue
            if len(key_text) > 120:
                raise ValueError("Ключ характеристики слишком длинный")
            cleaned[key_text] = item
        return cleaned


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    category: Optional[str] = Field(default=None, max_length=255)
    marketplace: Optional[Marketplace] = None
    sku: Optional[str] = Field(default=None, max_length=120)
    description: Optional[str] = Field(default=None, max_length=20000)
    attributes: Optional[Dict[str, Any]] = None

    @field_validator("name")
    @classmethod
    def _check_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = _strip(value)
        if not cleaned:
            raise ValueError("Название товара обязательно")
        return cleaned


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    name: str
    category: str
    marketplace: str
    sku: str
    description: str
    attributes: Dict[str, Any]
    is_demo: bool
    created_at: datetime
    updated_at: datetime


class ProductSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    category: str
    marketplace: str
    sku: str
    is_demo: bool
    created_at: datetime
    updated_at: datetime
    findings_total: int = 0
    findings_open: int = 0
    sources_total: int = 0
    last_run_at: Optional[datetime] = None
    last_run_status: Optional[str] = None
