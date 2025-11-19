import sys
import os

# Add project root to Python path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app

from db import get_db
from models.base import Base
from models.client_user import ClientUser
from models.hamasa_user import UserRole
from core.security import hash_password

# -----------------------------------------
# TEST DATABASE URL
# -----------------------------------------
TEST_DATABASE_URL = "sqlite:///./test.db"
# If you want PostgreSQL for tests:
# TEST_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/hamasa_test"


# -----------------------------------------
# Create test engine + session
# -----------------------------------------
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in TEST_DATABASE_URL else {}
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


# -----------------------------------------
# Override DB dependency in FastAPI
# -----------------------------------------
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db


# -----------------------------------------
# PYTEST GLOBAL SETUP
# -----------------------------------------
@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create tables before tests start."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


# -----------------------------------------
# Test Client
# -----------------------------------------
@pytest.fixture(scope="session")
def client():
    return TestClient(app)


# -----------------------------------------
# Seed Super Admin
# -----------------------------------------
SUPER_ADMIN_EMAIL = "admin@example.com"
SUPER_ADMIN_PASSWORD = "AdminPass123"

@pytest.fixture(scope="session", autouse=True)
def seed_super_admin():
    db = TestingSessionLocal()

    existing = db.query(ClientUser).filter_by(email=SUPER_ADMIN_EMAIL).first()
    if not existing:
        admin = ClientUser(
            email=SUPER_ADMIN_EMAIL,
            hashed_password=hash_password(SUPER_ADMIN_PASSWORD),
            role=UserRole.super_admin,
            is_active=True
        )
        db.add(admin)
        db.commit()

    db.close()


# -----------------------------------------
# Get Admin Token
# -----------------------------------------
@pytest.fixture(scope="session")
def admin_token(client):
    payload = {
        "email": SUPER_ADMIN_EMAIL,
        "password": SUPER_ADMIN_PASSWORD
    }

    res = client.post("/hamasa-api/v1/auth/login", json=payload)
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


# -----------------------------------------
# Authorized Client Fixture
# -----------------------------------------
@pytest.fixture
def auth_client(client, admin_token):
    client.headers.update({"Authorization": f"Bearer {admin_token}"})
    return client
