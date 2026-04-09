"""Test configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.main import app


@pytest.fixture
def test_db():
    """Create a test database."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestSessionLocal
    app.dependency_overrides.clear()


@pytest.fixture
def client(test_db):
    """Create a test client."""
    return TestClient(app)
