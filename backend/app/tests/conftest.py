"""Test configuration and fixtures."""

import uuid
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.connection import Base
from app.db.models import Document, User

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def test_db() -> Generator[Session, None, None]:
    """Create a test database session."""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user(test_db: Session) -> User:
    """Create a test user."""
    user = User(
        id=str(uuid.uuid4()),
        email="test@example.com",
        is_active=True,
        is_admin=False,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def test_admin_user(test_db: Session) -> User:
    """Create a test admin user."""
    user = User(
        id=str(uuid.uuid4()),
        email="admin@example.com",
        is_active=True,
        is_admin=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def test_document(test_db: Session) -> Document:
    """Create a test document."""
    doc = Document(
        id=str(uuid.uuid4()),
        title="Test CBT Document",
        source_type="markdown",
        content="""# Cognitive Behavioral Therapy

## What is CBT?

Cognitive Behavioral Therapy (CBT) is a type of psychotherapy that helps people identify and change negative thought patterns.

## Core Principles

1. **Thoughts affect feelings**: Our thoughts influence our emotions and behaviors.
2. **Cognitive distortions**: We often have biased ways of thinking.
3. **Behavioral activation**: Engaging in activities can improve mood.

## Common Techniques

### Thought Records

Keep track of negative thoughts and challenge them with evidence.

### Exposure Therapy

Gradually face feared situations in a controlled way.
""",
        extra_metadata={"source": "test"},
    )
    test_db.add(doc)
    test_db.commit()
    test_db.refresh(doc)
    return doc
