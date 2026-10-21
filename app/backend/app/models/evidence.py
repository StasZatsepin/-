"""Доказательство: фрагмент источника и его отношение к утверждению."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import EvidenceRelation, EvidenceType


class Evidence(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "evidence"

    product_id: Mapped[str] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_id: Mapped[str | None] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"), nullable=True, index=True
    )
    claim_id: Mapped[str | None] = mapped_column(
        ForeignKey("claims.id", ondelete="CASCADE"), nullable=True, index=True
    )

    evidence_type: Mapped[str] = mapped_column(
        default=EvidenceType.DESCRIPTION_TEXT.value, nullable=False
    )
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    relation: Mapped[str] = mapped_column(
        default=EvidenceRelation.UNCERTAIN.value, nullable=False
    )
    relevance_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    product: Mapped["Product"] = relationship(back_populates="evidence", lazy="joined")  # noqa: F821
    source: Mapped["Source | None"] = relationship(back_populates="evidence", lazy="joined")  # noqa: F821
