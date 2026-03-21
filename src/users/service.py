from sqlalchemy.orm import Session
from sqlalchemy import select
from src.db.models import User


class UsersService:
    def __init__(self, db: Session):
        self.db = db

    def find_by_username(self, username: str) -> User | None:
        # case-sensitive match — usernames are stored as is
        return self.db.execute(
            select(User).where(User.username == username)
        ).scalar_one_or_none()

    def find_by_id(self, user_id: str) -> User | None:
        return self.db.execute(
            select(User).where(User.id == user_id)
        ).scalar_one_or_none()

    def create(
        self,
        username: str,
        email: str,
        password_hash: str,
        role: str = 'USER',
    ) -> User:
        user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            role=role,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user