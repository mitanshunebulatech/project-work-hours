"""
app/services/search_service.py

Global search (⌘K command palette). Deliberately a thin composition
layer — no new query logic here, just calls the search() method each
repo already has (EmployeeProfileRepository/ProjectRepository/
DepartmentRepository) and shapes the combined result.

Permission-aware per category, not all-or-nothing on the whole endpoint:
employee results are only included if the requester has employees:view
(matching GET /employees's own gate) — departments and projects stay
open to any authenticated user, matching their own list endpoints, which
have no employees-specific sensitivity.
"""

from sqlalchemy.orm import Session

from app.core.deps import user_permission_codes
from app.db.repositories.department_repo import DepartmentRepository
from app.db.repositories.employee_profile_repo import EmployeeProfileRepository
from app.db.repositories.project_repo import ProjectRepository
from app.models.user import User
from app.schemas.search import SearchResponse, SearchResultItem

RESULTS_PER_CATEGORY = 5


class SearchService:
    def __init__(self, db: Session):
        self.db = db
        self.employee_repo = EmployeeProfileRepository(db)
        self.project_repo = ProjectRepository(db)
        self.department_repo = DepartmentRepository(db)

    def search(self, *, q: str, requesting_user: User) -> SearchResponse:
        results: list[SearchResultItem] = []

        if "employees:view" in user_permission_codes(requesting_user):
            employees, _ = self.employee_repo.search(search=q, limit=RESULTS_PER_CATEGORY, offset=0)
            results.extend(
                SearchResultItem(
                    category="employee",
                    id=e.id,
                    label=e.full_name,
                    sublabel=e.designation or e.employee_code,
                )
                for e in employees
            )

        projects, _ = self.project_repo.search(
            search=q, is_active=True, limit=RESULTS_PER_CATEGORY, offset=0
        )
        results.extend(
            SearchResultItem(category="project", id=p.id, label=p.project_name, sublabel=p.description)
            for p in projects
        )

        departments, _ = self.department_repo.search(
            search=q, is_active=True, limit=RESULTS_PER_CATEGORY, offset=0
        )
        results.extend(
            SearchResultItem(category="department", id=d.id, label=d.name, sublabel=None)
            for d in departments
        )

        return SearchResponse(query=q, results=results)
