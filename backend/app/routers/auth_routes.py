from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import create_token, get_current_user, hash_password, verify_password
from ..database import get_db
from ..db_models import User
from ..schemas import TokenResponse, UserCredentials, UserInfo

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(credentials: UserCredentials, db: Session = Depends(get_db)):
    username = credentials.username.strip()
    if len(username) < 3:
        raise HTTPException(400, "Username must be at least 3 characters.")
    if len(credentials.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters.")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(409, "Username is already taken.")

    # Public registration always creates a normal user; admins are made by
    # the seed script or promoted by another admin.
    user = User(username=username, password_hash=hash_password(credentials.password), role="user")
    db.add(user)
    db.commit()

    return TokenResponse(access_token=create_token(username), username=username, role=user.role)


@router.post("/login", response_model=TokenResponse)
def login(credentials: UserCredentials, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == credentials.username.strip()).first()
    if user is None or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(401, "Invalid username or password.")

    return TokenResponse(
        access_token=create_token(user.username), username=user.username, role=user.role
    )


@router.get("/me", response_model=UserInfo)
def me(user: User = Depends(get_current_user)):
    return UserInfo(
        id=user.id, username=user.username, role=user.role, created_at=user.created_at
    )
