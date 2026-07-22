"""
app/models/leave_policy.py
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LeavePolicy(Base):
    __tablename__ = "leave_policies"
    __table_args__ = (
        UniqueConstraint("leave_type_id", "effective_year", name="uq_policy_type_year"),
        CheckConstraint(
            "carry_forward_cap_days IS NULL OR carry_forward_cap_days <= annual_quota_days",
            name="chk_carry_forward_not_exceed_quota",
        ),
        Index("idx_leave_policies_type_year", "leave_type_id", "effective_year"),
        Index("idx_leave_policies_year", "effective_year"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    leave_type_id: Mapped[int] = mapped_column(ForeignKey("leave_types.id"), nullable=False)
    annual_quota_days: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    max_consecutive_days: Mapped[int] = mapped_column(Integer, nullable=False)
    min_notice_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    carry_forward_cap_days: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    carry_forward_expiry_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    accrual_frequency: Mapped[str] = mapped_column(String(20), nullable=False, default="upfront")
    effective_year: Mapped[int] = mapped_column(Integer, nullable=False)
    # HRMS V3: gates AnnualGrantService.run() per policy — added so the new
    # admin-input balance model (set at onboarding, edited in the Leave
    # Balance tab) can disable automatic annual granting for a leave type
    # without losing the policy's other config (max_consecutive_days,
    # carry_forward, etc.). Defaults True to preserve current behavior.
    auto_grant_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # WFH-specific: the "2 per month" figure. Deliberately separate from
    # annual_quota_days (which stays required-but-meaningless for WFH,
    # set to 0.00) — overloading one field with two different
    # cadences/meanings was rejected as more confusing than a second
    # nullable column.
    monthly_quota_days: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    leave_type = relationship("LeaveType", back_populates="policies")

    def __repr__(self) -> str:
        return (
            f"<LeavePolicy id={self.id} leave_type_id={self.leave_type_id} "
            f"year={self.effective_year}>"
        )
