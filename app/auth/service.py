from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.schemas import UserCreate
from app.auth.security import hash_password, verify_password


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Fetch a user by email."""
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, user_data: UserCreate) -> User:
    """
    Create a new user.

    Ensures unique email and stores a bcrypt-hashed password.
    """
    existing = get_user_by_email(db, user_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        email=user_data.email,
        name=user_data.name,
        hashed_password=hash_password(user_data.password),
        role="analyst",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """
    Authenticate a user by email and password.

    Returns the user on success, None otherwise.
    """
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user



