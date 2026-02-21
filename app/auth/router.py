import os
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session

from app.auth.schemas import UserCreate, UserLogin, UserResponse, TokenResponse
from app.auth.service import create_user, authenticate_user
from app.auth.security import create_access_token
from app.core.config import get_settings
from database.session import get_db


router = APIRouter(prefix="/auth", tags=["auth"])

# CORS origins — driven by env var, no hardcoded localhost
_ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001",
).split(",")


def _cors_response(request: Request) -> Response:
    """Create CORS response for preflight requests."""
    origin = request.headers.get("origin", "")

    # Use the request origin if it's in allowed list, otherwise use the first allowed origin
    allow_origin = origin if origin in _ALLOWED_ORIGINS else _ALLOWED_ORIGINS[0]

    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": allow_origin,
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, HEAD, PATCH",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "3600",
        },
    )


@router.options("/register")
async def options_register(request: Request):
    """Handle CORS preflight for /register."""
    return _cors_response(request)


@router.options("/login")
async def options_login(request: Request):
    """Handle CORS preflight for /login."""
    return _cors_response(request)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)) -> TokenResponse:
    """Register a new user and return JWT token."""
    user = create_user(db, user_in)
    
    settings = get_settings()
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
        },
        expires_delta=access_token_expires,
    )
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(user_in: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    """Authenticate user and return a JWT access token."""
    user = authenticate_user(db, user_in.email, user_in.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    settings = get_settings()
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
        },
        expires_delta=access_token_expires,
    )
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )



