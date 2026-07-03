"""Read-only view of the API-key pool for normal users.

Users pick a key by label to power the "Explain with AI" feature; they only
ever see the label and a masked tail, never the secret. Admins manage the
pool itself under /api/admin/api-keys.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..db_models import ApiKey, User
from ..schemas import ApiKeyOption

router = APIRouter(prefix="/api", tags=["keys"])


@router.get("/api-keys", response_model=list[ApiKeyOption])
def available_keys(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    keys = (
        db.query(ApiKey)
        .filter(ApiKey.is_active.is_(True))
        .order_by(ApiKey.label.asc())
        .all()
    )
    return [ApiKeyOption(id=k.id, label=k.label, masked=k.masked) for k in keys]
