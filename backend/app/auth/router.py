from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.schemas import SignupIn, StaffCreateIn, TokenOut, UserOut
from app.auth.security import (
    create_access_token,
    get_current_user,
    hash_password,
    require_roles,
    verify_password,
)
from app.core.db import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


def _create_user(db: Session, data: SignupIn, role: str) -> User:
    email = data.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = User(email=email, password_hash=hash_password(data.password), full_name=data.full_name, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(data: SignupIn, db: Session = Depends(get_db)):
    # Public signup always creates an applicant. Staff accounts come from /auth/staff.
    return _create_user(db, data, role="applicant")


@router.post("/login", response_model=TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # The form field is called "username" (OAuth2 standard); we put the email in it.
    user = db.scalar(select(User).where(User.email == form.username.lower()))
    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong email or password")
    return TokenOut(access_token=create_access_token(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/staff", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_staff(data: StaffCreateIn, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    return _create_user(db, data, role=data.role)