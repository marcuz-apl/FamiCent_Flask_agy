"""Test fixtures for FamiCent pytest suite.

Provides:
  - ``app``: Flask application configured for testing with in-memory SQLite.
  - ``client``: Flask test client.
  - ``db_session``: Raw SQLAlchemy session for in-memory test DB.
  - ``admin_user``: A seeded admin User instance.
  - ``auth_client``: A test client with a fully authenticated session.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from famicent.app import create_app
from famicent.auth.manager import hash_password
from famicent.db.engine import reset_engine
from famicent.db.models import Base, User, UserRole


# ---------------------------------------------------------------------------
# App / Client
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def app():
    """Create a Flask test application using in-memory SQLite (R49)."""
    test_app = create_app(
        test_config={
            "TESTING": True,
            "SECRET_KEY": "test-secret-key-do-not-use-in-prod",
            "DB_PATH": ":memory:",
            "SESSION_COOKIE_SECURE": False,
            "WTF_CSRF_ENABLED": False,
        }
    )
    reset_engine()  # Clear singleton so next test gets a fresh engine
    yield test_app
    reset_engine()


@pytest.fixture(scope="function")
def client(app):
    """Flask test client (R50)."""
    return app.test_client()


# ---------------------------------------------------------------------------
# Database Session
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def db_session() -> Session:
    """In-memory SQLAlchemy session for unit tests (R49)."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)


# ---------------------------------------------------------------------------
# Seeded Users
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def admin_user(db_session: Session) -> User:
    """Create and return a seeded admin user."""
    user = User(
        username="admin",
        role=UserRole.ADMIN,
        password_hash=hash_password("admin123").encode("utf-8"),
        password_changed=False,
        mfa_enabled=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def member_user(db_session: Session) -> User:
    """Create and return a seeded member user."""
    user = User(
        username="member1",
        role=UserRole.VIEWER,
        password_hash=hash_password("memberpass123").encode("utf-8"),
        password_changed=True,
        mfa_enabled=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Authenticated Client
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def auth_client(client, admin_user):
    """Test client with admin session pre-populated (bypasses login flow)."""
    with client.session_transaction() as sess:
        sess["user_id"] = admin_user.id
        sess["username"] = admin_user.username
        sess["role"] = admin_user.role
        sess["mfa_verified"] = True
        sess["password_changed"] = admin_user.password_changed
        from datetime import datetime
        sess["last_activity"] = datetime.utcnow().isoformat()
        sess["csrf_token"] = "test-csrf-token"
    return client
