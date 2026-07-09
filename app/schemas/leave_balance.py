"""
app/schemas/leave_balance.py
"""

from decimal import Decimal

from pydantic import BaseModel


class LeaveBalanceResponse(BaseModel):
    """
    Not a plain from_attributes model — assembled explicitly in the endpoint
    from LeaveBalance + its related LeaveType, since the dashboard needs the
    type's code/display_name alongside the numbers, not just leave_type_id.
    """

    leave_type_id: int
    leave_type_code: str
    leave_type_display_name: str
    year: int
    total_credited_days: Decimal
    total_debited_days: Decimal
    remaining_days: Decimal
