"""
main.py – Entry point for the Employee Work Hours Management System.

Run with:
    python main.py
"""

from nicegui import ui, app
from database import engine, get_db_session
from models import Base
from crud import seed_database
from ui import setup_ui


def init_db():
    """Create all tables and seed the database with sample data."""
    Base.metadata.create_all(bind=engine)
    db = get_db_session()
    try:
        seed_database(db)
    finally:
        db.close()


# Register all NiceGUI pages
setup_ui()


# Initialise the database before the server starts
@app.on_startup
async def startup():
    init_db()
    print("Database initialised. Sample data loaded.")
    print("Open http://localhost:8080 in your browser.")
    print("Admin login: admin / admin123")
    print("Employee logins: mitanshu/mitanshu123, om/om123, garv/garv123, ansih/anish123, vaibhav/vaibhav123")


ui.run(
    title="WorkHours",
    host="0.0.0.0",
    port=8081,
    storage_secret="work-hours-storage-secret-key",
    reload=False,
)
