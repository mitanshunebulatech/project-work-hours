"""prune leave_types to core five (CL, SL, Birthday, LOP, WFH)

Revision ID: 0015
Revises: 0014
Create Date: 2026-07-08 00:00:15

0013 seeded 10 leave types. Per updated requirements, only 5 are actually
wanted: Casual Leave, Sick Leave, Birthday Leave, Unpaid Leave (LOP), and
Work From Home. Rather than editing 0013 in place (that migration has
already been applied to real databases, per the project's own migration
history), this adds a new migration that deletes the unwanted rows —
Annual Leave, Maternity, Paternity, Comp Off, and Emergency — along with
their leave_policies rows. The five kept types retain their original IDs
(2, 3, 7, 8, 9) unchanged, so anything already referencing them is unaffected.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0015"
down_revision: Union[str, None] = "0014"
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

# ids being removed: 1=AL, 4=MATERNITY, 5=PATERNITY, 6=COMP_OFF, 10=EMERGENCY
REMOVED_TYPE_IDS = [1, 4, 5, 6, 10]

# Full original rows for these, kept here only so downgrade() can restore them.
REMOVED_TYPES = [
    (1, "AL", "Annual Leave", True, None, True),
    (4, "MATERNITY", "Maternity Leave", True, None, False),
    (5, "PATERNITY", "Paternity Leave", True, None, False),
    (6, "COMP_OFF", "Comp Off", True, None, True),
    (10, "EMERGENCY", "Emergency Leave", True, None, True),
]

REMOVED_POLICIES = {
    1: (18.00, 7, 7, 10.00, 3, "monthly"),
    4: (182.00, 182, 30, None, None, "upfront"),
    5: (7.00, 7, 7, None, None, "upfront"),
    6: (0.00, 3, 0, None, None, "earned"),
    10: (5.00, 3, 0, None, None, "upfront"),
}


def upgrade() -> None:
    # Any leave_requests already referencing these types would block a hard
    # delete (FK RESTRICT) — safe here because the module has no requests yet
    # at this point in the project's history. If this were run against a DB
    # with real leave requests already on these types, this migration would
    # correctly fail loudly rather than silently orphaning data.
    op.execute(
        sa.delete(leave_policies_table).where(
            leave_policies_table.c.leave_type_id.in_(REMOVED_TYPE_IDS)
        )
    )
    op.execute(sa.delete(leave_types_table).where(leave_types_table.c.id.in_(REMOVED_TYPE_IDS)))


def downgrade() -> None:
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
            for tid, code, name, paid, attach_after, half_day in REMOVED_TYPES
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
                "effective_year": 2026,
            }
            for tid, (quota, max_days, notice, cf_cap, cf_month, accrual) in REMOVED_POLICIES.items()
        ],
    )
