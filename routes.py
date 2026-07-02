"""
routes.py – FastAPI REST endpoints (optional / future use).

NiceGUI runs its own internal FastAPI app. If you want to expose a REST API
alongside the NiceGUI UI, add your APIRouter here and mount it in main.py.

Example:
    from fastapi import APIRouter, Depends
    from sqlalchemy.orm import Session
    from database import get_db
    from crud import get_all_entries

    router = APIRouter(prefix="/api", tags=["entries"])

    @router.get("/entries")
    def list_entries(db: Session = Depends(get_db)):
        return get_all_entries(db)
"""

# No REST routes are required for this project – all interaction happens
# through the NiceGUI pages defined in ui.py.
