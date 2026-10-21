"""add model explanation to findings

Пояснение внешней модели к находке. Колонки добавляются со значением по
умолчанию на стороне сервера: иначе существующие строки нарушили бы
ограничение NOT NULL.

Revision ID: 875f8d2cb164
Revises: 7ac1e79ffe5a
Create Date: 2026-10-21 20:40:39.719677

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '875f8d2cb164'
down_revision: Union[str, None] = '7ac1e79ffe5a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'findings',
        sa.Column(
            'explanation',
            sa.Text(),
            nullable=False,
            server_default=sa.text("''"),
        ),
    )
    op.add_column(
        'findings',
        sa.Column(
            'explanation_provider',
            sa.String(length=60),
            nullable=False,
            server_default=sa.text("''"),
        ),
    )
    # Значение по умолчанию больше не нужно: приложение всегда задаёт поле явно.
    op.alter_column('findings', 'explanation', server_default=None)
    op.alter_column('findings', 'explanation_provider', server_default=None)


def downgrade() -> None:
    op.drop_column('findings', 'explanation_provider')
    op.drop_column('findings', 'explanation')
