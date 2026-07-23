"""
app/api/v1/endpoints/search.py

GET /search?q=... — backend half of the ⌘K command palette. Open to any
authenticated user; per-category permission filtering happens inside
SearchService, not here (see its own docstring).
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.search import SearchResponse
from app.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("", response_model=SearchResponse)
def search(
    q: str = Query(min_length=1, max_length=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SearchResponse:
    return SearchService(db).search(q=q, requesting_user=current_user)
