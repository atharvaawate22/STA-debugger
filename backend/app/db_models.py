from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    # "admin" or "user"; controls access to the admin console and API-key pool.
    role: Mapped[str] = mapped_column(String(20), default="user")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    analyses: Mapped[list["Analysis"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    # Full AnalysisResult serialized as JSON; paths are read back as a whole,
    # never queried individually, so a normalized table would buy nothing.
    result_json: Mapped[str] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="analyses")


class ApiKey(Base):
    """A Groq API key managed centrally by admins.

    Normal users never see the secret — they pick a key by label from a
    dropdown, and the server substitutes the secret when calling Groq.
    """

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    label: Mapped[str] = mapped_column(String(80))
    secret: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    created_by: Mapped[str] = mapped_column(String(50))

    @property
    def masked(self) -> str:
        tail = self.secret[-4:] if len(self.secret) >= 4 else ""
        return f"••••{tail}"
