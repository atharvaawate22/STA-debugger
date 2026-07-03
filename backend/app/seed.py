"""Seed a first admin account on startup.

Idempotent: if any admin already exists, this does nothing. Otherwise it
creates one from STA_ADMIN_USERNAME / STA_ADMIN_PASSWORD (defaults in config),
promoting an existing account of that name rather than failing on a clash.
"""

from .auth import hash_password
from .config import SEED_ADMIN_PASSWORD, SEED_ADMIN_USERNAME
from .database import SessionLocal
from .db_models import User


def seed_admin() -> None:
    db = SessionLocal()
    try:
        if db.query(User).filter(User.role == "admin").first():
            return

        existing = db.query(User).filter(User.username == SEED_ADMIN_USERNAME).first()
        if existing:
            existing.role = "admin"
        else:
            db.add(User(
                username=SEED_ADMIN_USERNAME,
                password_hash=hash_password(SEED_ADMIN_PASSWORD),
                role="admin",
            ))
        db.commit()
    finally:
        db.close()
