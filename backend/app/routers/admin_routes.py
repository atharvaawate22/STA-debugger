"""Admin-only console: user management, cross-user history, the API-key pool,
and usage stats. Every route depends on get_current_admin, so a normal user's
token yields 403 here.
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import get_current_admin, hash_password
from ..database import get_db
from ..db_models import Analysis, ApiKey, User
from ..schemas import (
    AdminAnalysisItem,
    AdminUser,
    AdminUserCreate,
    AdminUserUpdate,
    ApiKeyAdmin,
    ApiKeyCreate,
    ApiKeyUpdate,
    UsageStats,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])

_VALID_ROLES = {"user", "admin"}


# ---------- users ----------

@router.get("/users", response_model=list[AdminUser])
def list_users(admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    counts = dict(
        db.query(Analysis.user_id, func.count(Analysis.id)).group_by(Analysis.user_id).all()
    )
    users = db.query(User).order_by(User.created_at.asc()).all()
    return [
        AdminUser(
            id=u.id,
            username=u.username,
            role=u.role,
            created_at=u.created_at,
            analysis_count=counts.get(u.id, 0),
        )
        for u in users
    ]


@router.post("/users", response_model=AdminUser, status_code=201)
def create_user(
    body: AdminUserCreate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    username = body.username.strip()
    if len(username) < 3:
        raise HTTPException(400, "Username must be at least 3 characters.")
    if len(body.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters.")
    if body.role not in _VALID_ROLES:
        raise HTTPException(400, "Role must be 'user' or 'admin'.")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(409, "Username is already taken.")

    user = User(
        username=username,
        password_hash=hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return AdminUser(
        id=user.id, username=user.username, role=user.role,
        created_at=user.created_at, analysis_count=0,
    )


@router.patch("/users/{user_id}", response_model=AdminUser)
def update_user(
    user_id: int,
    body: AdminUserUpdate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(404, "User not found.")

    if body.role is not None:
        if body.role not in _VALID_ROLES:
            raise HTTPException(400, "Role must be 'user' or 'admin'.")
        # Don't let the last admin demote themselves into a lockout.
        if user.id == admin.id and body.role != "admin":
            raise HTTPException(400, "You cannot remove your own admin role.")
        user.role = body.role

    if body.password is not None:
        if len(body.password) < 6:
            raise HTTPException(400, "Password must be at least 6 characters.")
        user.password_hash = hash_password(body.password)

    db.commit()
    db.refresh(user)
    count = db.query(func.count(Analysis.id)).filter(Analysis.user_id == user.id).scalar()
    return AdminUser(
        id=user.id, username=user.username, role=user.role,
        created_at=user.created_at, analysis_count=count,
    )


@router.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(404, "User not found.")
    if user.id == admin.id:
        raise HTTPException(400, "You cannot delete your own account.")
    db.delete(user)  # cascade removes their analyses
    db.commit()


# ---------- cross-user history ----------

@router.get("/analyses", response_model=list[AdminAnalysisItem])
def list_all_analyses(
    admin: User = Depends(get_current_admin), db: Session = Depends(get_db)
):
    rows = (
        db.query(Analysis, User.username)
        .join(User, Analysis.user_id == User.id)
        .order_by(Analysis.created_at.desc())
        .all()
    )
    items = []
    for analysis, username in rows:
        result = json.loads(analysis.result_json)
        items.append(AdminAnalysisItem(
            id=analysis.id,
            filename=analysis.filename,
            created_at=analysis.created_at,
            username=username,
            summary=result["summary"],
        ))
    return items


@router.delete("/analyses/{analysis_id}", status_code=204)
def delete_any_analysis(
    analysis_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if analysis is None:
        raise HTTPException(404, "Analysis not found.")
    db.delete(analysis)
    db.commit()


# ---------- API-key pool ----------

@router.get("/api-keys", response_model=list[ApiKeyAdmin])
def list_api_keys(admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    keys = db.query(ApiKey).order_by(ApiKey.created_at.desc()).all()
    return [
        ApiKeyAdmin(
            id=k.id, label=k.label, masked=k.masked,
            is_active=k.is_active, created_at=k.created_at, created_by=k.created_by,
        )
        for k in keys
    ]


@router.post("/api-keys", response_model=ApiKeyAdmin, status_code=201)
def create_api_key(
    body: ApiKeyCreate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    label = body.label.strip()
    secret = body.secret.strip()
    if not label:
        raise HTTPException(400, "A label is required.")
    if len(secret) < 8:
        raise HTTPException(400, "That does not look like a valid API key.")

    key = ApiKey(label=label, secret=secret, created_by=admin.username)
    db.add(key)
    db.commit()
    db.refresh(key)
    return ApiKeyAdmin(
        id=key.id, label=key.label, masked=key.masked,
        is_active=key.is_active, created_at=key.created_at, created_by=key.created_by,
    )


@router.patch("/api-keys/{key_id}", response_model=ApiKeyAdmin)
def update_api_key(
    key_id: int,
    body: ApiKeyUpdate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if key is None:
        raise HTTPException(404, "API key not found.")
    if body.label is not None:
        label = body.label.strip()
        if not label:
            raise HTTPException(400, "A label is required.")
        key.label = label
    if body.is_active is not None:
        key.is_active = body.is_active
    db.commit()
    db.refresh(key)
    return ApiKeyAdmin(
        id=key.id, label=key.label, masked=key.masked,
        is_active=key.is_active, created_at=key.created_at, created_by=key.created_by,
    )


@router.delete("/api-keys/{key_id}", status_code=204)
def delete_api_key(
    key_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if key is None:
        raise HTTPException(404, "API key not found.")
    db.delete(key)
    db.commit()


# ---------- stats ----------

@router.get("/stats", response_model=UsageStats)
def usage_stats(admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    total_users = db.query(func.count(User.id)).scalar()
    total_admins = db.query(func.count(User.id)).filter(User.role == "admin").scalar()
    total_analyses = db.query(func.count(Analysis.id)).scalar()
    active_keys = db.query(func.count(ApiKey.id)).filter(ApiKey.is_active.is_(True)).scalar()

    total_violations = 0
    for (result_json,) in db.query(Analysis.result_json).all():
        try:
            total_violations += json.loads(result_json)["summary"]["violated_paths"]
        except (KeyError, ValueError):
            continue

    return UsageStats(
        total_users=total_users,
        total_admins=total_admins,
        total_analyses=total_analyses,
        total_violations=total_violations,
        active_api_keys=active_keys,
    )
