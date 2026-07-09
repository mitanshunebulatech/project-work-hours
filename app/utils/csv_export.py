"""
app/utils/csv_export.py
"""

import csv
import io

from app.models.leave_request import LeaveRequest
from app.models.work_entry import WorkEntry


def entries_to_csv(entries: list[WorkEntry]) -> str:
    """
    Takes WorkEntry ORM objects with employee/project eagerly loaded
    and returns a CSV string ready to stream as a download.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "employee", "project", "date", "hours", "remarks", "status"])

    for entry in entries:
        writer.writerow(
            [
                entry.id,
                entry.employee.username,
                entry.project.project_name,
                entry.entry_date.isoformat(),
                float(entry.hours_worked),
                entry.remarks or "",
                entry.status,
            ]
        )

    return buffer.getvalue()


def leave_requests_to_csv(requests: list[LeaveRequest]) -> str:
    """
    Takes LeaveRequest ORM objects with employee/leave_type/reviewer eagerly
    loaded (see LeaveRequestRepository.search()) and returns a CSV string
    ready to stream as a download. reviewer is None for still-pending
    requests, handled the same way remarks/None is handled above.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "id",
            "employee",
            "leave_type",
            "start_date",
            "end_date",
            "working_days",
            "status",
            "reason",
            "reviewed_by",
            "admin_comment",
        ]
    )

    for req in requests:
        writer.writerow(
            [
                req.id,
                req.employee.username,
                req.leave_type.code,
                req.start_date.isoformat(),
                req.end_date.isoformat(),
                float(req.working_days_count),
                req.status,
                req.reason,
                req.reviewer.username if req.reviewer else "",
                req.admin_comment or "",
            ]
        )

    return buffer.getvalue()
