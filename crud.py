from sqlalchemy.orm import Session
from sqlalchemy import and_
from models import User, Project, WorkEntry
from auth import hash_password
from datetime import date as date_type


# ─── User operations ────────────────────────────────────────────────────────

def create_user(db: Session, username: str, password: str, role: str) -> User:
    user = User(username=username, password=hash_password(password), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_all_employees(db: Session):
    return db.query(User).filter(User.role == "employee").all()


def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


# ─── Project operations ──────────────────────────────────────────────────────

def create_project(db: Session, project_name: str) -> Project:
    project = Project(project_name=project_name.strip())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def get_all_projects(db: Session):
    return db.query(Project).order_by(Project.project_name).all()


def rename_project(db: Session, project_id: int, new_name: str) -> Project | None:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return None
    project.project_name = new_name.strip()
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project_id: int) -> bool:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return False
    db.delete(project)
    db.commit()
    return True


# ─── Work entry operations ───────────────────────────────────────────────────

def create_work_entry(
    db: Session,
    employee_id: int,
    project_id: int,
    entry_date: date_type,
    hours_worked: float,
    remarks: str = "",
) -> tuple[WorkEntry | None, str]:
    """
    Create a new work entry.
    Returns (entry, "") on success or (None, error_message) on failure.
    """
    # Duplicate check: same employee + project + date
    existing = db.query(WorkEntry).filter(
        and_(
            WorkEntry.employee_id == employee_id,
            WorkEntry.project_id == project_id,
            WorkEntry.date == entry_date,
        )
    ).first()
    if existing:
        return None, "An entry for this employee, project, and date already exists."

    entry = WorkEntry(
        employee_id=employee_id,
        project_id=project_id,
        date=entry_date,
        hours_worked=hours_worked,
        remarks=remarks,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry, ""


def get_entries_for_employee(db: Session, employee_id: int):
    return (
        db.query(WorkEntry)
        .filter(WorkEntry.employee_id == employee_id)
        .order_by(WorkEntry.date.desc())
        .all()
    )


def get_all_entries(db: Session):
    return (
        db.query(WorkEntry)
        .order_by(WorkEntry.date.desc())
        .all()
    )


def update_work_entry(
    db: Session,
    entry_id: int,
    project_id: int,
    entry_date: date_type,
    hours_worked: float,
    remarks: str,
) -> tuple[WorkEntry | None, str]:
    """
    Update an existing work entry.
    Returns (entry, "") on success or (None, error_message) on failure.
    """
    entry = db.query(WorkEntry).filter(WorkEntry.id == entry_id).first()
    if not entry:
        return None, "Entry not found."

    # Check duplicate only if employee/project/date combination changed
    duplicate = db.query(WorkEntry).filter(
        and_(
            WorkEntry.employee_id == entry.employee_id,
            WorkEntry.project_id == project_id,
            WorkEntry.date == entry_date,
            WorkEntry.id != entry_id,
        )
    ).first()
    if duplicate:
        return None, "Another entry for this employee, project, and date already exists."

    entry.project_id = project_id
    entry.date = entry_date
    entry.hours_worked = hours_worked
    entry.remarks = remarks
    db.commit()
    db.refresh(entry)
    return entry, ""


def delete_work_entry(db: Session, entry_id: int) -> bool:
    entry = db.query(WorkEntry).filter(WorkEntry.id == entry_id).first()
    if not entry:
        return False
    db.delete(entry)
    db.commit()
    return True


# ─── Seed data ───────────────────────────────────────────────────────────────

def seed_database(db: Session):
    """Populate the database with initial admin, employees, and projects if empty."""
    if db.query(User).count() > 0:
        return  # Already seeded

    # Admin
    create_user(db, "admin", "admin123", "admin")

    # Employees
    employee_names = ["mitanshu", "sahil", "garv", "anish", "vaibhav"]
    for name in employee_names:
        create_user(db, name, f"{name}123", "employee")

    # Projects
    project_names = [
        "Website Redesign",
        "Mobile App Development",
        "Data Migration",
        "API Integration",
        "Security Audit",
    ]
    for pname in project_names:
        if not db.query(Project).filter(Project.project_name == pname).first():
            create_project(db, pname)
