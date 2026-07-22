"""
app/services/leave_policy_rollover_service.py

Leave-wallet redesign follow-up: there was previously NO mechanism at all
that created next year's LeavePolicy rows — migration 0013 only ever
seeded the single year it ran in, and nothing has created one since. That
meant auto_grant_enabled (and every other policy field) would have had to
be manually re-entered by an admin for every future year, with no tooling
to do it at all.

This closes that gap generically, not just for auto_grant_enabled: for
every policy row effective in `from_year`, create a matching row for
`to_year` with all fields copied verbatim, unless a `to_year` row for
that leave_type_id already exists (idempotent — reruns and manually
pre-created rows are both left alone).
"""

from sqlalchemy.orm import Session

from app.db.repositories.leave_policy_repo import LeavePolicyRepository
from app.models.leave_policy import LeavePolicy


class LeavePolicyRolloverService:
    def __init__(self, db: Session):
        self.db = db
        self.policy_repo = LeavePolicyRepository(db)

    def run(self, *, from_year: int, to_year: int) -> dict:
        created = 0
        skipped = 0

        source_policies = self.policy_repo.list_for_year(year=from_year)
        existing_next_year = {
            p.leave_type_id for p in self.policy_repo.list_for_year(year=to_year)
        }

        for policy in source_policies:
            if policy.leave_type_id in existing_next_year:
                skipped += 1
                continue

            self.policy_repo.create(
                LeavePolicy(
                    leave_type_id=policy.leave_type_id,
                    annual_quota_days=policy.annual_quota_days,
                    max_consecutive_days=policy.max_consecutive_days,
                    min_notice_days=policy.min_notice_days,
                    carry_forward_cap_days=policy.carry_forward_cap_days,
                    carry_forward_expiry_month=policy.carry_forward_expiry_month,
                    accrual_frequency=policy.accrual_frequency,
                    effective_year=to_year,
                    auto_grant_enabled=policy.auto_grant_enabled,
                    monthly_quota_days=policy.monthly_quota_days,
                )
            )
            created += 1

        self.db.commit()
        return {"from_year": from_year, "to_year": to_year, "created": created, "skipped": skipped}
