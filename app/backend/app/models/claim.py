"""Утверждение продавца и привязка к фрагменту источника."""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ClaimType, ConfidenceStatus, ExtractionMethod


class Claim(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "claims"

    product_id: Mapped[str] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_id: Mapped[str | None] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"), nullable=True, index=True
    )

    text: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[str] = mapped_column(default=ClaimType.OTHER.value, nullable=False)
    source_excerpt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    start_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)

    extraction_method: Mapped[str] = mapped_column(
        default=ExtractionMethod.RULE_BASED.value, nullable=False
    )
    model_version: Mapped[str | None] = mapped_column(String(200), nullable=True)
    confidence_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confidence_status: Mapped[str] = mapped_column(
        default=ConfidenceStatus.NEEDS_REVIEW.value, nullable=False
    )

    user_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_rejected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    numeric_value: Mapped[float | None] = mapped_column(nullable=True)
    numeric_unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    numeric_dimension: Mapped[str | None] = mapped_column(String(50), nullable=True)
    numeric_comparator: Mapped[str | None] = mapped_column(String(30), nullable=True)
    numeric_context: Mapped[str | None] = mapped_column(Text, nullable=True)

    product: Mapped["Product"] = relationship(back_populates="claims", lazy="joined")  # noqa: F821
    source: Mapped["Source | None"] = relationship(back_populates="claims", lazy="joined")  # noqa: F821
