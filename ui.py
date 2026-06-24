"""
ui.py – All NiceGUI pages for the Employee Work Hours Management System.
"""

from nicegui import ui, app
from datetime import date, datetime
from sqlalchemy.orm import Session

from database import get_db_session
from auth import authenticate_user
from crud import (
    get_all_projects,
    get_entries_for_employee,
    get_all_entries,
    get_all_employees,
    create_work_entry,
    update_work_entry,
    delete_work_entry,
    create_project,
    rename_project,
    delete_project,
)


# ─── Shared helpers ──────────────────────────────────────────────────────────

BRAND_BLUE = "#1E3A5F"
ACCENT = "#2563EB"
BG = "#F0F4F8"
CARD_BG = "#FFFFFF"
DANGER = "#DC2626"
SUCCESS_COLOR = "#16A34A"


def page_wrapper(title: str):
    """Apply shared page-level styles and title."""
    ui.query("body").style(f"background:{BG}; font-family:'Inter',sans-serif; margin:0;")
    ui.html(f"<title>{title}</title>")


def nav_bar(username: str, role: str):
    """Top navigation bar shared by both dashboards."""
    with ui.row().classes("w-full items-center justify-between px-6 py-3").style(
        f"background:{BRAND_BLUE}; box-shadow:0 2px 6px rgba(0,0,0,.25);"
    ):
        ui.label("⏱  WorkHours").style(
            "color:#FFFFFF; font-size:1.25rem; font-weight:700; letter-spacing:.5px;"
        )
        with ui.row().classes("items-center gap-4"):
            ui.label(f"👤 {username}").style("color:#CBD5E1; font-size:.9rem;")
            ui.label(f"[{role.upper()}]").style("color:#93C5FD; font-size:.75rem; font-weight:600;")
            ui.button("Logout", on_click=lambda: (app.storage.user.clear(), ui.navigate.to("/"))).props(
                "flat dense"
            ).style("color:#FCA5A5; font-weight:600;")


def section_card(title: str):
    """Return a styled card container with a section title."""
    with ui.card().classes("w-full").style(
        f"background:{CARD_BG}; border-radius:12px;"
        "box-shadow:0 1px 6px rgba(0,0,0,.10); padding:24px; margin-bottom:20px;"
    ) as card:
        ui.label(title).style(
            f"color:{BRAND_BLUE}; font-size:1.05rem; font-weight:700; margin-bottom:16px; display:block;"
        )
    return card


def notify_success(msg: str):
    ui.notify(msg, type="positive", position="top", timeout=3000)


def notify_error(msg: str):
    ui.notify(msg, type="negative", position="top", timeout=4000)


# ─── Login page ──────────────────────────────────────────────────────────────

def setup_login_page():
    @ui.page("/")
    def login_page():
        page_wrapper("WorkHours – Login")

        with ui.column().classes("items-center justify-center").style(
            f"min-height:100vh; background:linear-gradient(135deg,{BRAND_BLUE} 0%,#2563EB 100%);"
        ):
            # Card
            with ui.card().style(
                "width:380px; border-radius:16px; padding:36px 32px;"
                "box-shadow:0 8px 32px rgba(0,0,0,.30);"
            ):
                # Logo / heading
                ui.label("⏱").style("font-size:2.5rem; text-align:center; display:block; margin-bottom:4px;")
                ui.label("WorkHours").style(
                    f"font-size:1.6rem; font-weight:800; color:{BRAND_BLUE};"
                    "text-align:center; display:block; margin-bottom:4px;"
                )
                ui.label("Employee Work Hours Management").style(
                    "font-size:.8rem; color:#64748B; text-align:center;"
                    "display:block; margin-bottom:28px;"
                )

                username_input = ui.input(label="Username", placeholder="Enter your username").classes("w-full").style("margin-bottom:12px;")
                username_input.props('outlined dense')

                password_input = ui.input(label="Password", placeholder="Enter your password", password=True, password_toggle_button=True).classes("w-full").style("margin-bottom:20px;")
                password_input.props('outlined dense')

                error_label = ui.label("").style(f"color:{DANGER}; font-size:.85rem; min-height:20px; display:block; margin-bottom:8px;")

                def do_login():
                    username = username_input.value.strip()
                    password = password_input.value

                    if not username or not password:
                        error_label.set_text("Please enter both username and password.")
                        return

                    db: Session = get_db_session()
                    try:
                        user = authenticate_user(db, username, password)
                        if not user:
                            error_label.set_text("Invalid username or password.")
                            return

                        # Store session data
                        app.storage.user["user_id"] = user.id
                        app.storage.user["username"] = user.username
                        app.storage.user["role"] = user.role

                        if user.role == "admin":
                            ui.navigate.to("/admin")
                        else:
                            ui.navigate.to("/employee")
                    finally:
                        db.close()

                ui.button("Sign In", on_click=do_login).classes("w-full").style(
                    f"background:{ACCENT}; color:white; font-weight:700;"
                    "border-radius:8px; height:42px; font-size:1rem;"
                ).props("no-caps")

                ui.label("Default admin: admin / admin123").style(
                    "color:#94A3B8; font-size:.72rem; text-align:center;"
                    "display:block; margin-top:20px;"
                )


# ─── Employee dashboard ──────────────────────────────────────────────────────

def setup_employee_page():
    @ui.page("/employee")
    def employee_page():
        user_id = app.storage.user.get("user_id")
        username = app.storage.user.get("username")
        role = app.storage.user.get("role")

        if not user_id or role != "employee":
            ui.navigate.to("/")
            return

        page_wrapper("WorkHours – Employee Dashboard")
        nav_bar(username, role)

        with ui.column().classes("w-full px-6 py-6").style("max-width:900px; margin:0 auto;"):

            # ── Submission form ──────────────────────────────────────────────
            with ui.card().style(
                f"background:{CARD_BG}; border-radius:12px;"
                "box-shadow:0 1px 6px rgba(0,0,0,.10); padding:28px; margin-bottom:24px; width:100%;"
            ):
                ui.label("Log Work Hours").style(
                    f"color:{BRAND_BLUE}; font-size:1.1rem; font-weight:700; margin-bottom:18px; display:block;"
                )

                # Employee name (read-only)
                name_input = ui.input(label="Employee Name", value=username).classes("w-full").style("margin-bottom:12px;")
                name_input.props("outlined dense readonly")

                # Date picker
                date_input = ui.input(
                    label="Date",
                    value=date.today().isoformat(),
                    placeholder="YYYY-MM-DD",
                ).classes("w-full").style("margin-bottom:12px;")
                date_input.props("outlined dense")
                with date_input:
                    with ui.menu().props("no-parent-event") as date_menu:
                        with ui.date(value=date.today().isoformat()).bind_value(date_input) as date_picker:
                            with ui.row().classes("justify-end"):
                                ui.link("Close").on("click", date_menu.close)
                    with date_input.add_slot("append"):
                        ui.icon("edit_calendar").on("click", date_menu.open).classes("cursor-pointer")

                # Project dropdown
                db_temp: Session = get_db_session()
                try:
                    projects = get_all_projects(db_temp)
                    project_options = {p.project_name: p.id for p in projects}
                finally:
                    db_temp.close()

                project_select = ui.select(
                    label="Project",
                    options=list(project_options.keys()) if project_options else [],
                ).classes("w-full").style("margin-bottom:12px;")
                project_select.props("outlined dense")

                # Hours worked
                hours_input = ui.number(label="Hours Worked", min=0, max=24, precision=1).classes("w-full").style("margin-bottom:12px;")
                hours_input.props("outlined dense")

                # Remarks
                remarks_input = ui.textarea(label="Remarks (optional)").classes("w-full").style("margin-bottom:18px;")
                remarks_input.props("outlined dense rows=2")

                status_label = ui.label("").style("min-height:20px; font-size:.85rem; margin-bottom:8px; display:block;")

                # Entries table reference (will be built below)
                entries_table_ref = {"table": None}

                def refresh_entries_table():
                    """Reload entries table for this employee."""
                    if entries_table_ref["table"] is None:
                        return
                    db: Session = get_db_session()
                    try:
                        entries = get_entries_for_employee(db, user_id)
                        rows = [
                            {
                                "date": str(e.date),
                                "project": e.project.project_name if e.project else "—",
                                "hours": e.hours_worked,
                                "remarks": e.remarks or "",
                            }
                            for e in entries
                        ]
                        entries_table_ref["table"].rows = rows
                        entries_table_ref["table"].update()
                    finally:
                        db.close()

                def submit_entry():
                    # Validation
                    if not date_input.value:
                        status_label.style(f"color:{DANGER};")
                        status_label.set_text("Please select a date.")
                        return
                    try:
                        entry_date = datetime.strptime(date_input.value, "%Y-%m-%d").date()
                    except ValueError:
                        status_label.style(f"color:{DANGER};")
                        status_label.set_text("Invalid date format. Use YYYY-MM-DD.")
                        return

                    if not project_select.value:
                        status_label.style(f"color:{DANGER};")
                        status_label.set_text("Please select a project.")
                        return

                    if hours_input.value is None:
                        status_label.style(f"color:{DANGER};")
                        status_label.set_text("Please enter hours worked.")
                        return
                    hours = float(hours_input.value)
                    if hours <= 0:
                        status_label.style(f"color:{DANGER};")
                        status_label.set_text("Hours must be greater than 0.")
                        return
                    if hours > 24:
                        status_label.style(f"color:{DANGER};")
                        status_label.set_text("Hours cannot exceed 24.")
                        return

                    project_id = project_options.get(project_select.value)
                    if not project_id:
                        status_label.style(f"color:{DANGER};")
                        status_label.set_text("Invalid project selected.")
                        return

                    db: Session = get_db_session()
                    try:
                        entry, error = create_work_entry(
                            db,
                            employee_id=user_id,
                            project_id=project_id,
                            entry_date=entry_date,
                            hours_worked=hours,
                            remarks=remarks_input.value or "",
                        )
                        if error:
                            status_label.style(f"color:{DANGER};")
                            status_label.set_text(error)
                        else:
                            status_label.style(f"color:{SUCCESS_COLOR};")
                            status_label.set_text("✓ Entry submitted successfully!")
                            # Reset form fields
                            date_input.value = date.today().isoformat()
                            project_select.value = None
                            hours_input.value = None
                            remarks_input.value = ""
                            refresh_entries_table()
                    finally:
                        db.close()

                ui.button("Submit Entry", on_click=submit_entry).style(
                    f"background:{ACCENT}; color:white; font-weight:700; border-radius:8px; height:40px;"
                ).props("no-caps")

            # ── My Entries table ─────────────────────────────────────────────
            with ui.card().style(
                f"background:{CARD_BG}; border-radius:12px;"
                "box-shadow:0 1px 6px rgba(0,0,0,.10); padding:28px; width:100%;"
            ):
                ui.label("My Work Entries").style(
                    f"color:{BRAND_BLUE}; font-size:1.1rem; font-weight:700; margin-bottom:18px; display:block;"
                )

                columns = [
                    {"name": "date", "label": "Date", "field": "date", "sortable": True},
                    {"name": "project", "label": "Project", "field": "project", "sortable": True},
                    {"name": "hours", "label": "Hours Worked", "field": "hours", "sortable": True},
                    {"name": "remarks", "label": "Remarks", "field": "remarks"},
                ]

                db: Session = get_db_session()
                try:
                    initial_entries = get_entries_for_employee(db, user_id)
                    initial_rows = [
                        {
                            "date": str(e.date),
                            "project": e.project.project_name if e.project else "—",
                            "hours": e.hours_worked,
                            "remarks": e.remarks or "",
                        }
                        for e in initial_entries
                    ]
                finally:
                    db.close()

                table = ui.table(
                    columns=columns,
                    rows=initial_rows,
                    row_key="date",
                    pagination=10,
                ).classes("w-full").style("font-size:.9rem;")
                table.props("flat bordered")
                entries_table_ref["table"] = table

                if not initial_rows:
                    ui.label("No entries yet. Submit your first entry above.").style(
                        "color:#94A3B8; font-size:.9rem; margin-top:8px;"
                    )


# ─── Admin dashboard ─────────────────────────────────────────────────────────

def setup_admin_page():
    @ui.page("/admin")
    def admin_page():
        user_id = app.storage.user.get("user_id")
        username = app.storage.user.get("username")
        role = app.storage.user.get("role")

        if not user_id or role != "admin":
            ui.navigate.to("/")
            return

        page_wrapper("WorkHours – Admin Dashboard")
        nav_bar(username, role)

        with ui.column().classes("w-full px-6 py-6").style("max-width:1200px; margin:0 auto;"):

            # ── Section 1: Work Records ──────────────────────────────────────
            ui.label("Section 1 — Employee Work Records").style(
                f"color:{BRAND_BLUE}; font-size:1.25rem; font-weight:800; margin-bottom:16px; display:block;"
            )

            # Filter controls
            with ui.card().style(
                f"background:{CARD_BG}; border-radius:12px;"
                "box-shadow:0 1px 6px rgba(0,0,0,.10); padding:20px; margin-bottom:16px; width:100%;"
            ):
                ui.label("Filter & Search").style(
                    "color:#475569; font-size:.85rem; font-weight:600; margin-bottom:12px; display:block;"
                )
                with ui.row().classes("w-full gap-3 flex-wrap items-end"):
                    search_input = ui.input(label="Search", placeholder="Search any field...").style("min-width:180px;")
                    search_input.props("outlined dense")

                    # Employee filter options
                    db_temp: Session = get_db_session()
                    try:
                        all_employees = get_all_employees(db_temp)
                        all_projects_list = get_all_projects(db_temp)
                        emp_options = ["All"] + [e.username for e in all_employees]
                        proj_options_list = ["All"] + [p.project_name for p in all_projects_list]
                    finally:
                        db_temp.close()

                    emp_filter = ui.select(label="Employee", options=emp_options, value="All").style("min-width:150px;")
                    emp_filter.props("outlined dense")

                    proj_filter = ui.select(label="Project", options=proj_options_list, value="All").style("min-width:160px;")
                    proj_filter.props("outlined dense")

                    date_from = ui.input(label="Date From", placeholder="YYYY-MM-DD").style("min-width:140px;")
                    date_from.props("outlined dense")

                    date_to = ui.input(label="Date To", placeholder="YYYY-MM-DD").style("min-width:140px;")
                    date_to.props("outlined dense")

                    ui.button("Apply Filters", on_click=lambda: apply_filters()).style(
                        f"background:{ACCENT}; color:white; font-weight:600; border-radius:8px; height:38px;"
                    ).props("no-caps")
                    ui.button("Clear", on_click=lambda: clear_filters()).props("flat no-caps").style(
                        "height:38px; color:#64748B;"
                    )

            # Work entries table
            with ui.card().style(
                f"background:{CARD_BG}; border-radius:12px;"
                "box-shadow:0 1px 6px rgba(0,0,0,.10); padding:20px; margin-bottom:32px; width:100%;"
            ):
                work_columns = [
                    {"name": "id", "label": "ID", "field": "id", "sortable": True},
                    {"name": "employee", "label": "Employee", "field": "employee", "sortable": True},
                    {"name": "date", "label": "Date", "field": "date", "sortable": True},
                    {"name": "project", "label": "Project", "field": "project", "sortable": True},
                    {"name": "hours", "label": "Hours", "field": "hours", "sortable": True},
                    {"name": "remarks", "label": "Remarks", "field": "remarks"},
                    {"name": "actions", "label": "Actions", "field": "actions"},
                ]

                work_table_ref = {"table": None, "all_rows": []}

                def load_all_entries() -> list[dict]:
                    db: Session = get_db_session()
                    try:
                        entries = get_all_entries(db)
                        return [
                            {
                                "id": e.id,
                                "employee": e.employee.username if e.employee else "—",
                                "date": str(e.date),
                                "project": e.project.project_name if e.project else "—",
                                "hours": e.hours_worked,
                                "remarks": e.remarks or "",
                            }
                            for e in entries
                        ]
                    finally:
                        db.close()

                work_table_ref["all_rows"] = load_all_entries()

                work_table = ui.table(
                    columns=work_columns,
                    rows=work_table_ref["all_rows"],
                    row_key="id",
                    pagination=10,
                ).classes("w-full").style("font-size:.875rem;")
                work_table.props("flat bordered")
                work_table_ref["table"] = work_table

                # Action buttons slot (Edit / Delete per row)
                work_table.add_slot("body-cell-actions", r"""
                    <q-td :props="props">
                        <q-btn flat dense icon="edit" color="primary"
                               @click="$parent.$emit('edit-entry', props.row)" />
                        <q-btn flat dense icon="delete" color="negative"
                               @click="$parent.$emit('delete-entry', props.row)" />
                    </q-td>
                """)

                def apply_filters():
                    rows = work_table_ref["all_rows"]
                    query = search_input.value.strip().lower()
                    emp_val = emp_filter.value
                    proj_val = proj_filter.value
                    df = date_from.value.strip()
                    dt = date_to.value.strip()

                    filtered = []
                    for row in rows:
                        if emp_val and emp_val != "All" and row["employee"] != emp_val:
                            continue
                        if proj_val and proj_val != "All" and row["project"] != proj_val:
                            continue
                        if df:
                            try:
                                if str(row["date"]) < df:
                                    continue
                            except Exception:
                                pass
                        if dt:
                            try:
                                if str(row["date"]) > dt:
                                    continue
                            except Exception:
                                pass
                        if query:
                            combined = " ".join(str(v).lower() for v in row.values())
                            if query not in combined:
                                continue
                        filtered.append(row)

                    work_table.rows = filtered
                    work_table.update()

                def clear_filters():
                    search_input.value = ""
                    emp_filter.value = "All"
                    proj_filter.value = "All"
                    date_from.value = ""
                    date_to.value = ""
                    work_table.rows = work_table_ref["all_rows"]
                    work_table.update()

                def refresh_work_table():
                    work_table_ref["all_rows"] = load_all_entries()
                    work_table.rows = work_table_ref["all_rows"]
                    work_table.update()

                # ── Edit dialog ─────────────────────────────────────────────
                with ui.dialog() as edit_dialog, ui.card().style("min-width:360px; padding:24px;"):
                    ui.label("Edit Work Entry").style(
                        f"font-size:1.05rem; font-weight:700; color:{BRAND_BLUE}; margin-bottom:16px; display:block;"
                    )
                    edit_entry_id = {"value": None}

                    edit_date_input = ui.input(label="Date", placeholder="YYYY-MM-DD").classes("w-full").style("margin-bottom:10px;")
                    edit_date_input.props("outlined dense")

                    db_temp2: Session = get_db_session()
                    try:
                        edit_projects = get_all_projects(db_temp2)
                        edit_proj_options = {p.project_name: p.id for p in edit_projects}
                    finally:
                        db_temp2.close()

                    edit_project_select = ui.select(label="Project", options=list(edit_proj_options.keys())).classes("w-full").style("margin-bottom:10px;")
                    edit_project_select.props("outlined dense")

                    edit_hours = ui.number(label="Hours Worked", min=0, max=24, precision=1).classes("w-full").style("margin-bottom:10px;")
                    edit_hours.props("outlined dense")

                    edit_remarks = ui.textarea(label="Remarks").classes("w-full").style("margin-bottom:16px;")
                    edit_remarks.props("outlined dense rows=2")

                    edit_error = ui.label("").style(f"color:{DANGER}; font-size:.82rem; min-height:18px; display:block; margin-bottom:8px;")

                    def save_edit():
                        entry_id = edit_entry_id["value"]
                        if not entry_id:
                            return
                        try:
                            entry_date = datetime.strptime(edit_date_input.value, "%Y-%m-%d").date()
                        except ValueError:
                            edit_error.set_text("Invalid date format.")
                            return
                        if not edit_project_select.value:
                            edit_error.set_text("Please select a project.")
                            return
                        if edit_hours.value is None or float(edit_hours.value) <= 0:
                            edit_error.set_text("Hours must be > 0.")
                            return
                        if float(edit_hours.value) > 24:
                            edit_error.set_text("Hours cannot exceed 24.")
                            return

                        proj_id = edit_proj_options.get(edit_project_select.value)
                        db: Session = get_db_session()
                        try:
                            _, error = update_work_entry(
                                db, entry_id, proj_id, entry_date,
                                float(edit_hours.value), edit_remarks.value or ""
                            )
                            if error:
                                edit_error.set_text(error)
                            else:
                                edit_dialog.close()
                                refresh_work_table()
                                notify_success("Entry updated successfully.")
                        finally:
                            db.close()

                    with ui.row().classes("gap-3"):
                        ui.button("Save", on_click=save_edit).style(
                            f"background:{ACCENT}; color:white; font-weight:600; border-radius:6px;"
                        ).props("no-caps")
                        ui.button("Cancel", on_click=edit_dialog.close).props("flat no-caps").style("color:#64748B;")

                def handle_edit(e):
                    row = e.args
                    edit_entry_id["value"] = row["id"]
                    edit_date_input.value = row["date"]
                    edit_project_select.value = row["project"]
                    edit_hours.value = row["hours"]
                    edit_remarks.value = row["remarks"]
                    edit_error.set_text("")
                    edit_dialog.open()

                work_table.on("edit-entry", handle_edit)

                # ── Delete confirmation ─────────────────────────────────────
                delete_entry_id = {"value": None}

                with ui.dialog() as delete_dialog, ui.card().style("padding:24px; min-width:300px;"):
                    ui.label("Delete this entry?").style(
                        f"font-size:1rem; font-weight:700; color:{BRAND_BLUE}; margin-bottom:8px; display:block;"
                    )
                    ui.label("This action cannot be undone.").style("color:#64748B; font-size:.88rem; margin-bottom:20px; display:block;")
                    with ui.row().classes("gap-3"):
                        def confirm_delete():
                            eid = delete_entry_id["value"]
                            if eid is None:
                                return
                            db: Session = get_db_session()
                            try:
                                delete_work_entry(db, eid)
                            finally:
                                db.close()
                            delete_dialog.close()
                            refresh_work_table()
                            notify_success("Entry deleted.")

                        ui.button("Delete", on_click=confirm_delete).style(
                            f"background:{DANGER}; color:white; font-weight:600; border-radius:6px;"
                        ).props("no-caps")
                        ui.button("Cancel", on_click=delete_dialog.close).props("flat no-caps").style("color:#64748B;")

                def handle_delete(e):
                    row = e.args
                    delete_entry_id["value"] = row["id"]
                    delete_dialog.open()

                work_table.on("delete-entry", handle_delete)

            # ── Section 2: Project Management ────────────────────────────────
            ui.label("Section 2 — Project Management").style(
                f"color:{BRAND_BLUE}; font-size:1.25rem; font-weight:800; margin-bottom:16px; display:block;"
            )

            with ui.card().style(
                f"background:{CARD_BG}; border-radius:12px;"
                "box-shadow:0 1px 6px rgba(0,0,0,.10); padding:24px; width:100%;"
            ):
                # Add project row
                with ui.row().classes("items-center gap-3 w-full").style("margin-bottom:20px;"):
                    new_project_input = ui.input(label="New Project Name", placeholder="e.g. Backend Overhaul").style("flex:1;")
                    new_project_input.props("outlined dense")
                    proj_error_label = ui.label("").style(f"color:{DANGER}; font-size:.82rem; min-width:180px;")

                proj_table_ref = {"table": None}

                def load_projects_rows() -> list[dict]:
                    db: Session = get_db_session()
                    try:
                        projects = get_all_projects(db)
                        return [{"id": p.id, "name": p.project_name} for p in projects]
                    finally:
                        db.close()

                def refresh_proj_table():
                    proj_table_ref["table"].rows = load_projects_rows()
                    proj_table_ref["table"].update()

                def add_project():
                    name = new_project_input.value.strip()
                    if not name:
                        proj_error_label.set_text("Project name cannot be empty.")
                        return
                    db: Session = get_db_session()
                    try:
                        from sqlalchemy import and_
                        from models import Project as PModel
                        existing = db.query(PModel).filter(PModel.project_name == name).first()
                        if existing:
                            proj_error_label.set_text(f'"{name}" already exists.')
                            return
                        create_project(db, name)
                        new_project_input.value = ""
                        proj_error_label.set_text("")
                        refresh_proj_table()
                        notify_success(f'Project "{name}" created.')
                    finally:
                        db.close()

                with ui.row().classes("items-center gap-3").style("margin-bottom:20px;"):
                    ui.button("Add Project", on_click=add_project).style(
                        f"background:{SUCCESS_COLOR}; color:white; font-weight:600; border-radius:8px; height:38px;"
                    ).props("no-caps icon=add")
                    proj_error_label  # rendered inline

                proj_columns = [
                    {"name": "id", "label": "ID", "field": "id", "sortable": True, "style": "width:60px;"},
                    {"name": "name", "label": "Project Name", "field": "name", "sortable": True},
                    {"name": "actions", "label": "Actions", "field": "actions"},
                ]

                proj_table = ui.table(
                    columns=proj_columns,
                    rows=load_projects_rows(),
                    row_key="id",
                ).classes("w-full").style("font-size:.9rem;")
                proj_table.props("flat bordered")
                proj_table_ref["table"] = proj_table

                proj_table.add_slot("body-cell-actions", r"""
                    <q-td :props="props">
                        <q-btn flat dense icon="edit" color="primary"
                               @click="$parent.$emit('rename-project', props.row)" />
                        <q-btn flat dense icon="delete" color="negative"
                               @click="$parent.$emit('delete-project', props.row)" />
                    </q-td>
                """)

                # ── Rename dialog ───────────────────────────────────────────
                rename_proj_id = {"value": None}

                with ui.dialog() as rename_dialog, ui.card().style("padding:24px; min-width:320px;"):
                    ui.label("Rename Project").style(
                        f"font-size:1rem; font-weight:700; color:{BRAND_BLUE}; margin-bottom:16px; display:block;"
                    )
                    rename_input = ui.input(label="New Name").classes("w-full").style("margin-bottom:16px;")
                    rename_input.props("outlined dense")
                    rename_error = ui.label("").style(f"color:{DANGER}; font-size:.82rem; min-height:18px; margin-bottom:8px; display:block;")

                    def save_rename():
                        pid = rename_proj_id["value"]
                        new_name = rename_input.value.strip()
                        if not new_name:
                            rename_error.set_text("Name cannot be empty.")
                            return
                        db: Session = get_db_session()
                        try:
                            result = rename_project(db, pid, new_name)
                            if not result:
                                rename_error.set_text("Project not found.")
                            else:
                                rename_dialog.close()
                                refresh_proj_table()
                                notify_success(f'Project renamed to "{new_name}".')
                        finally:
                            db.close()

                    with ui.row().classes("gap-3"):
                        ui.button("Save", on_click=save_rename).style(
                            f"background:{ACCENT}; color:white; font-weight:600; border-radius:6px;"
                        ).props("no-caps")
                        ui.button("Cancel", on_click=rename_dialog.close).props("flat no-caps").style("color:#64748B;")

                def handle_rename(e):
                    row = e.args
                    rename_proj_id["value"] = row["id"]
                    rename_input.value = row["name"]
                    rename_error.set_text("")
                    rename_dialog.open()

                proj_table.on("rename-project", handle_rename)

                # ── Delete project confirmation ──────────────────────────────
                delete_proj_id = {"value": None}

                with ui.dialog() as del_proj_dialog, ui.card().style("padding:24px; min-width:300px;"):
                    ui.label("Delete this project?").style(
                        f"font-size:1rem; font-weight:700; color:{BRAND_BLUE}; margin-bottom:8px; display:block;"
                    )
                    ui.label("All associated work entries will also be deleted.").style(
                        "color:#64748B; font-size:.88rem; margin-bottom:20px; display:block;"
                    )
                    with ui.row().classes("gap-3"):
                        def confirm_del_proj():
                            pid = delete_proj_id["value"]
                            if pid is None:
                                return
                            db: Session = get_db_session()
                            try:
                                delete_project(db, pid)
                            finally:
                                db.close()
                            del_proj_dialog.close()
                            refresh_proj_table()
                            notify_success("Project deleted.")

                        ui.button("Delete", on_click=confirm_del_proj).style(
                            f"background:{DANGER}; color:white; font-weight:600; border-radius:6px;"
                        ).props("no-caps")
                        ui.button("Cancel", on_click=del_proj_dialog.close).props("flat no-caps").style("color:#64748B;")

                def handle_del_proj(e):
                    row = e.args
                    delete_proj_id["value"] = row["id"]
                    del_proj_dialog.open()

                proj_table.on("delete-project", handle_del_proj)


# ─── Register all pages ───────────────────────────────────────────────────────

def setup_ui():
    setup_login_page()
    setup_employee_page()
    setup_admin_page()
