import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.db.models import Base
from src.db.session import get_db
from main import app
import os

TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/vg_analytics"
)

engine = create_engine(TEST_DB_URL)
TestSession = sessionmaker(bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_client(client):
    client.post("/api/auth/register", json={
        "username": "testuser",
        "email": "test@test.com",
        "password": "testpass123"
    })
    r = client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "testpass123"
    })
    token = r.json().get("access_token", "")
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client