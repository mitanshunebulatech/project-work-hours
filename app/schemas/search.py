"""
app/schemas/search.py

Global search (⌘K command palette, backend half). One flat list with a
`category` discriminator rather than three separate lists — the frontend
groups by category for display either way, and a flat list is simpler to
cap at an overall result count if that's ever wanted later.
"""

from pydantic import BaseModel


class SearchResultItem(BaseModel):
    category: str  # "employee" | "project" | "department"
    id: int
    label: str
    sublabel: str | None = None


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]
