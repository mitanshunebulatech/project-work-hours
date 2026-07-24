"""add timezone to users (Settings page)

Revision ID: 0030
Revises: 0029
Create Date: 2026-07-24 00:00:30

Settings page (HRMS V3, "broader: theme, timezone, other account prefs").
Theme is client-side only (localStorage, no backend state — see
useTheme.tsx) so it needs nothing here. email_notifications_enabled
already exists on users (added earlier, previously unused by any
endpoint). timezone is the one genuinely new field.

Stored as an IANA timezone string (e.g. "Asia/Kolkata"), not a UTC
offset — offsets don't account for DST and aren't stable identifiers.
Defaults to "UTC" for every existing row rather than guessing a real
timezone for users who never set one.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0030"
down_revision: Union[str, None] = "0029"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("timezone", sa.String(length=50), nullable=False, server_default="UTC"),
    )
    op.alter_column("users", "timezone", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "timezone")
