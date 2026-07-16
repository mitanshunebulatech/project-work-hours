"""
tests/unit/test_work_schedule_policy.py
Pure schema-validation tests for WorkSchedulePolicyUpdate — no DB needed.
"""

from datetime import time

import pytest
from pydantic import ValidationError

from app.schemas.work_schedule_policy import WorkSchedulePolicyUpdate


def test_default_company_hours_are_valid():
    policy = WorkSchedulePolicyUpdate(
        first_half_start=time(11, 0), first_half_end=time(16, 0),
        second_half_start=time(16, 0), second_half_end=time(20, 0),
    )
    assert policy.first_half_start == time(11, 0)
    assert policy.second_half_end == time(20, 0)


def test_first_half_end_must_be_after_start():
    with pytest.raises(ValidationError):
        WorkSchedulePolicyUpdate(
            first_half_start=time(16, 0), first_half_end=time(11, 0),
            second_half_start=time(16, 0), second_half_end=time(20, 0),
        )


def test_second_half_end_must_be_after_start():
    with pytest.raises(ValidationError):
        WorkSchedulePolicyUpdate(
            first_half_start=time(11, 0), first_half_end=time(16, 0),
            second_half_start=time(20, 0), second_half_end=time(16, 0),
        )


def test_second_half_cannot_start_before_first_half_ends():
    with pytest.raises(ValidationError):
        WorkSchedulePolicyUpdate(
            first_half_start=time(11, 0), first_half_end=time(16, 0),
            second_half_start=time(15, 0), second_half_end=time(20, 0),
        )


def test_back_to_back_halves_are_allowed():
    """second_half_start exactly equal to first_half_end (no gap, no overlap) is valid."""
    policy = WorkSchedulePolicyUpdate(
        first_half_start=time(11, 0), first_half_end=time(16, 0),
        second_half_start=time(16, 0), second_half_end=time(20, 0),
    )
    assert policy.second_half_start == policy.first_half_end
