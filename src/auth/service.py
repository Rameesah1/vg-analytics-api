import bcrypt
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from src.users.service import UsersService
from src.auth.dependencies import create_access_token
from src.auth.schemas import SignUpSchema, SignInSchema, AuthResponseSchema


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UsersService(db)

    def register(self, dto: SignUpSchema) -> AuthResponseSchema:
        # check username isn't already taken
        if self.users.find_by_username(dto.username):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already exists",
            )

        password_hash = hash_password(dto.password)
        user = self.users.create(
            username=dto.username,
            email=dto.email,
            password_hash=password_hash,
        )

        token = create_access_token({
            "sub": str(user.id),
            "username": user.username,
            "role": user.role,
        })
        return AuthResponseSchema(access_token=token)

    def login(self, dto: SignInSchema) -> AuthResponseSchema:
        user = self.users.find_by_username(dto.username)

        # deliberately vague error — don't reveal whether username exists
        if not user or not verify_password(dto.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        token = create_access_token({
            "sub": str(user.id),
            "username": user.username,
            "role": user.role,
        })
        return AuthResponseSchema(access_token=token)