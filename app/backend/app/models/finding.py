"""Находка: потенциальное противоречие или недостаток данных."""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ConfidenceStatus, FindingStatus, FindingType, Severity


class Finding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "findings"

    product_id: Mapped[str] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    claim_id: Mapped[str | None] = mapped_column(
        ForeignKey("claims.id", ondelete="SET NULL"), nullable=True, index=True
    )
    analysis_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )

    finding_type: Mapped[str] = mapped_column(nullable=False)
    severity: Mapped[str] = mapped_column(default=Severity.LOW.value, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)

    source_evidence_ids: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    source_refs: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    limitations: Mapped[str] = mapped_column(Text, default="", nullable=False)
    recommended_action: Mapped[str] = mapped_column(Text, default="", nullable=False)
    confidence_status: Mapped[str] = mapped_column(
        default=ConfidenceStatus.NEEDS_REVIEW.value, nullable=False
    )

    status: Mapped[str] = mapped_column(default=FindingStatus.OPEN.value, nullable=False)
    rule_id: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    rule_version: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    origin: Mapped[str] = mapped_column(String(60), default="rules", nullable=False)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    product: Mapped["Product"] = relationship(back_populates="findings", lazy="joined")  # noqa: F821
    claim: Mapped["Claim | None"] = relationship(lazy="joined")  # noqa: F821
    review_actions: Mapped[list["ReviewAction"]] = relationship(  # noqa: F821
        back_populates="finding", cascade="all, delete-orphan", lazy="select"
    )
