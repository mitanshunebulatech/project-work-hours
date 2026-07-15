"""
tests/integration/test_dashboard_service.py
"""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.leave_request import LeaveRequest
from app.models.work_entry import WorkEntry
from app.services.dashboard_service import DashboardService


def test_today_timesheets_counts_only_todays_entries(db_session: Session, seeded_users, seeded_project):
    today = date.today()
    yesterday = today - timedelta(days=1)

    db_session.add_all(
        [
            WorkEntry(
                employee_id=seeded_users["alice"].id,
                project_id=seeded_project.id,
                entry_date=today,
                hours_worked=Decimal("4.00"),
                status="pending",
            ),
            WorkEntry(
                employee_id=seeded_users["bob"].id,
                project_id=seeded_project.id,
                entry_date=today,
                hours_worked=Decimal("3.50"),
                status="approved",
            ),
            # Yesterday's entry must not leak into "today's" numbers.
            WorkEntry(
                employee_id=seeded_users["alice"].id,
                project_id=seeded_project.id,
                entry_date=yesterday,
                hours_worked=Decimal("8.00"),
                status="approved",
            ),
        ]
    )
    db_session.commit()

    summary = DashboardService(db_session).get_summary()

    assert summary.today == today
    assert summary.today_timesheets.total_entries == 2
    assert summary.today_timesheets.total_hours == 7.5
    # Only the "pending" one dated today counts — matches the PM decision
    # that this widget is today-scoped, not the full backlog.
    assert summary.today_timesheets.pending_approvals == 1


def test_employees_on_leave_today_and_missing_timesheets_are_mutually_exclusive(
    db_session: Session, seeded_users, seeded_project, seeded_leave_type
):
    today = date.today()

    # Bob is on approved leave today — should appear in "on leave today"
    # and must NOT appear in "missing timesheets" even though he logged no hours.
    db_session.add(
        LeaveRequest(
            employee_id=seeded_users["bob"].id,
            leave_type_id=seeded_leave_type.id,
            start_date=today,
            end_date=today,
            is_half_day=False,
            working_days_count=Decimal("1.00"),
            reason="Personal",
            status="approved",
        )
    )
    # Alice logged no hours today and is not on leave — she IS missing.
    db_session.commit()

    summary = DashboardService(db_session).get_summary()

    on_leave_ids = {e.employee_id for e in summary.employees_on_leave_today}
    missing_ids = {e.employee_id for e in summary.missing_timesheets}

    assert seeded_users["bob"].id in on_leave_ids
    assert seeded_users["bob"].id not in missing_ids
    assert seeded_users["alice"].id in missing_ids
    assert seeded_users["alice"].id not in on_leave_ids


def test_recent_activities_merges_and_sorts_timesheets_and_leave_newest_first(
    db_session: Session, seeded_users, seeded_project, seeded_leave_type
):
    today = date.today()

    entry = WorkEntry(
        employee_id=seeded_users["alice"].id,
        project_id=seeded_project.id,
        entry_date=today,
        hours_worked=Decimal("2.00"),
        status="pending",
    )
    db_session.add(entry)
    db_session.commit()

    leave = LeaveRequest(
        employee_id=seeded_users["bob"].id,
        leave_type_id=seeded_leave_type.id,
        start_date=today + timedelta(days=3),
        end_date=today + timedelta(days=3),
        is_half_day=False,
        working_days_count=Decimal("1.00"),
        reason="Trip",
        status="pending",
    )
    db_session.add(leave)
    db_session.commit()

    summary = DashboardService(db_session).get_summary()

    types_seen = {a.activity_type for a in summary.recent_activities}
    assert "timesheet" in types_seen
    assert "leave_request" in types_seen
    # Newest-first: whichever was committed last (leave, since it was added
    # second) should not be sorted behind the earlier timesheet entry.
    occurred_ats = [a.occurred_at for a in summary.recent_activities]
    assert occurred_ats == sorted(occurred_ats, reverse=True)


def test_leave_calendar_this_month_reuses_calendar_query(
    db_session: Session, seeded_users, seeded_leave_type
):
    today = date.today()
    db_session.add(
        LeaveRequest(
            employee_id=seeded_users["alice"].id,
            leave_type_id=seeded_leave_type.id,
            start_date=today,
            end_date=today,
            is_half_day=False,
            working_days_count=Decimal("1.00"),
            reason="Personal",
            status="approved",
        )
    )
    db_session.commit()

    summary = DashboardService(db_session).get_summary()

    assert len(summary.leave_calendar_this_month) == 1
    assert summary.leave_calendar_this_month[0].employee_name == "alice"
