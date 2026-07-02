"""
app/api/v1/endpoints/profile.py
Separate from users.py because users.py is admin-only at the router level (FR-A06).
This satisfies FR-E08: any authenticated user can view their own profile.
"""

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.user import ProfileResponse

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("/me", response_model=ProfileResponse)
def get_my_profile(current_user: User = Depends(get_current_user)) -> ProfileResponse:
    return ProfileResponse.model_validate(current_user)
