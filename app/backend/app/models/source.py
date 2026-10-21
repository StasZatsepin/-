"""Источник данных товара: загруженный файл, описание, таблица характеристик."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ExtractionMethod, ExtractionStatus, SourceType


class Source(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sources"

    product_id: Mapped[str] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )

    source_type: Mapped[str] = mapped_column(
        default=SourceType.OTHER.value, nullable=False
    )
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_uri: Mapped[str | None] = mapped_column(Text, nullable=True)

    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    extraction_method: Mapped[str] = mapped_column(
        default=ExtractionMethod.RULE_BASED.value, nullable=False
    )
    extraction_status: Mapped[str] = mapped_column(
        default=ExtractionStatus.PENDING.value, nullable=False
    )
    extraction_note: Mapped[str] = mapped_column(Text, default="", nullable=False)

    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(200), nullable=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    text_content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)

    product: Mapped["Product"] = relationship(back_populates="sources", lazy="joined")  # noqa: F821
    claims: Mapped[list["Claim"]] = relationship(  # noqa: F821
        back_populates="source", cascade="all, delete-orphan", lazy="select"
    )
    evidence: Mapped[list["Evidence"]] = relationship(  # noqa: F821
        back_populates="source", cascade="all, delete-orphan", lazy="select"
    )
