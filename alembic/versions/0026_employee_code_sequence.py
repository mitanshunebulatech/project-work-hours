"""create employee_code_seq for atomic employee code generation

Revision ID: 0026
Revises: 0025
Create Date: 2026-07-17 00:00:26

Fixes a real concurrency bug found during a repo audit:
EmployeeProfileRepository.generate_next_employee_code() computes the next
code via SELECT MAX(employee_code) + 1 in application code. Two onboarding
requests arriving concurrently can both read the same MAX before either
commits, and both compute the same "next" code — the UNIQUE constraint on
employee_code then rejects the second INSERT, turning a legitimate
onboarding request into an unexplained 500.

A Postgres SEQUENCE is atomic under concurrency by construction. This
migration only adds the sequence — it does not touch any existing column
or table, so it's a purely additive, zero-downtime change.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0026"
down_revision: Union[str, None] = "0025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE IF NOT EXISTS employee_code_seq START 1")
    # Advance the sequence past any codes already issued via the old MAX+1
    # logic, so the first nextval() after this migration can't collide.
    op.execute(
        """
        SELECT setval(
            'employee_code_seq',
            GREATEST(
                1,
                COALESCE(
                    (SELECT MAX(CAST(split_part(employee_code, '-', 2) AS INTEGER))
                     FROM employee_profiles
                     WHERE employee_code ~ '^EMP-[0-9]+$'),
                    0
                )
            )
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP SEQUENCE IF EXISTS employee_code_seq")
