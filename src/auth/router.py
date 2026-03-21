from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.db.session import get_db
from src.db.models import User
from src.auth.service import AuthService
from src.auth.schemas import SignUpSchema, SignInSchema, AuthResponseSchema, UserProfileSchema
from src.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=AuthResponseSchema,
    status_code=201,
    summary="Register a new user and receive a JWT token",
    responses={409: {"description": "Username already exists"}},
)
def register(dto: SignUpSchema, db: Session = Depends(get_db)):
    return AuthService(db).register(dto)


@router.post(
    "/login",
    response_model=AuthResponseSchema,
    summary="Login and receive a JWT token",
    responses={401: {"description": "Invalid credentials"}},
)
def login(dto: SignInSchema, db: Session = Depends(get_db)):
    return AuthService(db).login(dto)


@router.get(
    "/me",
    response_model=UserProfileSchema,
    summary="Get current user profile",
    responses={401: {"description": "Unauthorised"}},
)
def me(current_user: User = Depends(get_current_user)):
    # never return password_hash - only expose safe fields
    return current_user