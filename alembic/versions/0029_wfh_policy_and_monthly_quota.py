"""add monthly_quota_days to leave_policies, create WFH policy row

Revision ID: 0029
Revises: 0028
Create Date: 2026-07-23 00:00:29

Completes the leave-wallet redesign started in 0028 (auto_grant_enabled +
leave_plans hard-drop): WFH never had a policy row (see migration 0013 —
meaning WFH previously had ZERO limits of any kind, not "broken", just
unrestricted). It gets one now so its request-time validation
(max_consecutive_days/min_notice_days) and balance check actually engage
— both are gated on "a policy row exists" in leave_service.py.

annual_quota_days is required-but-meaningless for WFH here (set to 0.00)
since auto_grant_enabled=False routes it away from AnnualGrantService
entirely — WFH is credited by a separate monthly mechanism (its own
service, a later stage), not the annual grant job.

Deliberately does NOT touch CL/SL/Birthday's auto_grant_enabled (0028
already made the call to leave those at the default True until the
admin-input Leave Balance UI actually exists, so this migration doesn't
undo or second-guess that sequencing decision).
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0029"
down_revision: Union[str, None] = "0028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

leave_policies_table = sa.table(
    "leave_policies",
    sa.column("leave_type_id", sa.Integer),
    sa.column("annual_quota_days", sa.Numeric),
    sa.column("max_consecutive_days", sa.Integer),
    sa.column("min_notice_days", sa.Integer),
    sa.column("carry_forward_cap_days", sa.Numeric),
    sa.column("carry_forward_expiry_month", sa.Integer),
    sa.column("accrual_frequency", sa.String),
    sa.column("effective_year", sa.Integer),
    sa.column("auto_grant_enabled", sa.Boolean),
    sa.column("monthly_quota_days", sa.Numeric),
)

WFH_LEAVE_TYPE_ID = 8


def upgrade() -> None:
    from datetime import date

    current_year = date.today().year

    op.add_column(
        "leave_policies",
        sa.Column("monthly_quota_days", sa.Numeric(5, 2), nullable=True),
    )

    conn = op.get_bind()

    # Idempotent: a WFH policy row for this year may already exist (e.g.
    # from a prior partial/failed run of this exact migration) — never
    # overwrite an existing row's other values, only fill the gap if it's
    # genuinely missing.
    existing = conn.execute(
        sa.select(leave_policies_table.c.leave_type_id).where(
            leave_policies_table.c.leave_type_id == WFH_LEAVE_TYPE_ID,
            leave_policies_table.c.effective_year == current_year,
        )
    ).first()

    if existing is None:
        conn.execute(
            leave_policies_table.insert().values(
                leave_type_id=WFH_LEAVE_TYPE_ID,
                annual_quota_days=0.00,
                max_consecutive_days=2,
                min_notice_days=0,
                carry_forward_cap_days=None,
                carry_forward_expiry_month=None,
                accrual_frequency="monthly",
                effective_year=current_year,
                auto_grant_enabled=False,
                monthly_quota_days=2.00,
            )
        )
    else:
        # Row already existed (from the earlier failed attempt) before
        # monthly_quota_days existed as a column — backfill just that value.
        conn.execute(
            leave_policies_table.update()
            .where(
                leave_policies_table.c.leave_type_id == WFH_LEAVE_TYPE_ID,
                leave_policies_table.c.effective_year == current_year,
            )
            .values(monthly_quota_days=2.00)
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        leave_policies_table.delete().where(
            leave_policies_table.c.leave_type_id == WFH_LEAVE_TYPE_ID
        )
    )
    op.drop_column("leave_policies", "monthly_quota_days")
