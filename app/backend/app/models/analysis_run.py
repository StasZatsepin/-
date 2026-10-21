"""Запуск анализа товара: версия правил, провайдер, сводка результата."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AnalysisStatus


class AnalysisRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "analysis_runs"

    product_id: Mapped[str] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )

    status: Mapped[str] = mapped_column(default=AnalysisStatus.PENDING.value, nullable=False)
    engine_version: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    rules_version: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    provider_name: Mapped[str] = mapped_column(String(60), default="mock", nullable=False)
    provider_status: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    triggered_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    summary: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    limitations: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, default="", nullable=False)

    product: Mapped["Product"] = relationship(back_populates="analysis_runs", lazy="joined")  # noqa: F821
