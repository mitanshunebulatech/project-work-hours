"""
app/utils/name_utils.py

Shared full_name -> (first_name, last_name) splitting logic. Used by
EmployeeProfileService (admin create/update, which still accepts a single
full_name string for convenience) and, later, OnboardingService. Mirrors the
same split-on-first-space rule used to backfill existing rows in migration
0025 — kept in one place so the two never drift apart.
"""


def split_full_name(full_name: str) -> tuple[str, str | None]:
    """
    Splits "Alice Sharma" -> ("Alice", "Sharma"); "Cher" -> ("Cher", None);
    "Mary Jane Watson" -> ("Mary", "Jane Watson") — everything after the
    first space becomes last_name, same as the SQL backfill in 0025.
    """
    normalized = full_name.strip()
    if " " not in normalized:
        return normalized, None
    first, remainder = normalized.split(" ", 1)
    remainder = remainder.strip()
    return first, remainder or None
