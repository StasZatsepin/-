"""Товар: описание, категория, маркетплейс и структурированные характеристики."""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import Marketplace


class Product(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "products"

    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    marketplace: Mapped[str] = mapped_column(
        default=Marketplace.OTHER.value, nullable=False
    )
    sku: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    attributes: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    sources: Mapped[list["Source"]] = relationship(  # noqa: F821
        back_populates="product", cascade="all, delete-orphan", lazy="select"
    )
    claims: Mapped[list["Claim"]] = relationship(  # noqa: F821
        back_populates="product", cascade="all, delete-orphan", lazy="select"
    )
    evidence: Mapped[list["Evidence"]] = relationship(  # noqa: F821
        back_populates="product", cascade="all, delete-orphan", lazy="select"
    )
    findings: Mapped[list["Finding"]] = relationship(  # noqa: F821
        back_populates="product", cascade="all, delete-orphan", lazy="select"
    )
    analysis_runs: Mapped[list["AnalysisRun"]] = relationship(  # noqa: F821
        back_populates="product", cascade="all, delete-orphan", lazy="select"
    )
