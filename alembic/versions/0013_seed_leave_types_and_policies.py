"""seed leave_types and leave_policies

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-07 00:00:13

Note: LOP (Loss of Pay) and WFH (Work From Home) deliberately get no
leave_policies row — LOP has no quota by design (it's the unpaid fallback,
always available) and WFH doesn't debit any balance at all (see Phase 3/4
of the design discussion). Every other type gets one policy row scoped to
the current year, matching the "policy per type per year" design so past
requests always resolve against the policy that was actually in force.
"""

from datetime import date
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

leave_types_table = sa.table(
    "leave_types",
    sa.column("id", sa.Integer),
    sa.column("code", sa.String),
    sa.column("display_name", sa.String),
    sa.column("is_paid", sa.Boolean),
    sa.column("requires_attachment_after_days", sa.Integer),
    sa.column("allows_half_day", sa.Boolean),
    sa.column("is_active", sa.Boolean),
)

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
)

CURRENT_YEAR = date.today().year

# id : (code, display_name, is_paid, requires_attachment_after_days, allows_half_day)
LEAVE_TYPES = [
    (1, "AL", "Annual Leave", True, None, True),
    (2, "CL", "Casual Leave", True, None, True),
    (3, "SL", "Sick Leave", True, 3, True),
    (4, "MATERNITY", "Maternity Leave", True, None, False),
    (5, "PATERNITY", "Paternity Leave", True, None, False),
    (6, "COMP_OFF", "Comp Off", True, None, True),
    (7, "LOP", "Loss of Pay", False, None, True),
    (8, "WFH", "Work From Home", True, None, True),
    (9, "BIRTHDAY", "Birthday Leave", True, None, False),
    (10, "EMERGENCY", "Emergency Leave", True, None, True),
]

# leave_type_id : (quota, max_consecutive, min_notice, carry_fwd_cap, carry_fwd_expiry_month, accrual)
POLICIES = {
    1: (18.00, 7, 7, 10.00, 3, "monthly"),      # AL
    2: (12.00, 3, 1, None, None, "upfront"),     # CL
    3: (12.00, 7, 0, None, None, "upfront"),     # SL — no advance notice; illness isn't planned
    4: (182.00, 182, 30, None, None, "upfront"), # Maternity — 26 weeks
    5: (7.00, 7, 7, None, None, "upfront"),      # Paternity
    6: (0.00, 3, 0, None, None, "earned"),       # Comp Off — earned dynamically, no upfront quota
    9: (1.00, 1, 0, None, None, "upfront"),      # Birthday
    10: (5.00, 3, 0, None, None, "upfront"),     # Emergency
    # 7 (LOP) and 8 (WFH) intentionally have no policy row — see module docstring.
}


def upgrade() -> None:
    op.bulk_insert(
        leave_types_table,
        [
            {
                "id": tid,
                "code": code,
                "display_name": name,
                "is_paid": paid,
                "requires_attachment_after_days": attach_after,
                "allows_half_day": half_day,
                "is_active": True,
            }
            for tid, code, name, paid, attach_after, half_day in LEAVE_TYPES
        ],
    )

    op.bulk_insert(
        leave_policies_table,
        [
            {
                "leave_type_id": tid,
                "annual_quota_days": quota,
                "max_consecutive_days": max_days,
                "min_notice_days": notice,
                "carry_forward_cap_days": cf_cap,
                "carry_forward_expiry_month": cf_month,
                "accrual_frequency": accrual,
                "effective_year": CURRENT_YEAR,
            }
            for tid, (quota, max_days, notice, cf_cap, cf_month, accrual) in POLICIES.items()
        ],
    )

    op.execute("SELECT setval('leave_types_id_seq', (SELECT MAX(id) FROM leave_types))")


def downgrade() -> None:
    op.execute("DELETE FROM leave_policies")
    op.execute("DELETE FROM leave_types")
