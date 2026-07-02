"""
app/utils/csv_export.py
"""

import csv
import io

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
