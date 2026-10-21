import io
import zipfile
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.main import app
from backend.app.database import Base, get_db
from backend.app.models.user import User
from backend.app.core.security import get_password_hash, create_access_token

# In-memory SQLite for testing
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def init_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def admin_user(db_session):
    user = User(
        email="test_admin@phoenix.io",
        hashed_password=get_password_hash("password123"),
        full_name="Test Admin",
        role="admin"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def dev_user(db_session):
    user = User(
        email="test_dev@phoenix.io",
        hashed_password=get_password_hash("password123"),
        full_name="Test Developer",
        role="developer"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def other_user(db_session):
    user = User(
        email="test_other@phoenix.io",
        hashed_password=get_password_hash("password123"),
        full_name="Other Developer",
        role="developer"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def admin_token(admin_user):
    return create_access_token({"sub": admin_user.id, "role": admin_user.role, "email": admin_user.email})

@pytest.fixture
def dev_token(dev_user):
    return create_access_token({"sub": dev_user.id, "role": dev_user.role, "email": dev_user.email})

@pytest.fixture
def other_token(other_user):
    return create_access_token({"sub": other_user.id, "role": other_user.role, "email": other_user.email})

@pytest.fixture
def sample_buggy_zip():
    """Generates an in-memory ZIP containing a Python project with a reproducible bug and unit test."""
    calculator_code = """def calculate_total(items):
    total = 0
    for item in items:
        total += item
    return total
"""
    test_code = """from calculator import calculate_total

def test_calculate_total_numbers():
    assert calculate_total([10, 20, 30]) == 60

def test_calculate_total_none():
    # Bug: when items is None, raises TypeError
    assert calculate_total(None) == 0
"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("calculator.py", calculator_code)
        zf.writestr("test_calc.py", test_code)
        zf.writestr("requirements.txt", "pytest\n")
    buf.seek(0)
    return buf.getvalue()
