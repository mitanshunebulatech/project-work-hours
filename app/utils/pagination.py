"""
app/utils/pagination.py
Shared Depends() for page/size query params, clamped to MAX_PAGE_SIZE.
"""

from fastapi import Query

from app.core.config import settings


class PageParams:
    def __init__(
        self,
        page: int = Query(1, ge=1),
        size: int = Query(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE),
    ):
        self.page = page
        self.size = size
