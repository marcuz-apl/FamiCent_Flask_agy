"""Flask application factory for FamiCent.

Creates and configures the Flask app, registers blueprints, sets up the
database, seeds the admin user on first run, and applies security headers.
"""
from __future__ import annotations

import logging
import os
import secrets
from pathlib import Path

from flask import Flask, g, request, session
from sqlalchemy.orm import Session as DbSession

from famicent.db.engine import get_engine, get_session
from famicent.db.models import Base, User, UserRole

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_DEFAULT_SECRET_KEY_FILE = Path(__file__).parent.parent.parent / ".flask_secret"
_DB_DIR = Path(__file__).parent.parent.parent / "data"
_DB_PATH = _DB_DIR / "famicent.db"


def _load_or_create_secret_key() -> str:
    """Load Flask secret key from file, or generate and persist a new one."""
    if _DEFAULT_SECRET_KEY_FILE.exists():
        return _DEFAULT_SECRET_KEY_FILE.read_text(encoding="utf-8").strip()
    key = secrets.token_hex(32)
    _DEFAULT_SECRET_KEY_FILE.write_text(key, encoding="utf-8")
    logger.info("Generated new Flask secret key.")
    return key


def _seed_admin(db: DbSession) -> None:
    """Create the default admin user if one does not exist (FR-USR-MGT-01)."""
    from sqlalchemy import select

    from famicent.auth.manager import hash_password
    from famicent.utils.helpers import DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USERNAME

    existing = db.execute(
        select(User).where(User.username == DEFAULT_ADMIN_USERNAME)
    ).scalar_one_or_none()
    if existing is None:
        admin = User(
            username=DEFAULT_ADMIN_USERNAME,
            role=UserRole.ADMIN,
            password_hash=hash_password(DEFAULT_ADMIN_PASSWORD).encode("utf-8"),
            password_changed=False,
            mfa_enabled=False,
        )
        db.add(admin)
        db.commit()
        logger.info("Default admin user seeded.")


def create_app(test_config: dict | None = None) -> Flask:
    """Application factory.

    Args:
        test_config: Optional mapping of config overrides (used in tests).

    Returns:
        A configured Flask application instance.
    """
    app = Flask(__name__, static_folder="static", template_folder="templates")

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    app.config["SECRET_KEY"] = _load_or_create_secret_key()
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Strict"
    app.config["SESSION_COOKIE_SECURE"] = False  # localhost only
    app.config["PERMANENT_SESSION_LIFETIME"] = 300  # 5-minute sessions
    app.config["DB_PATH"] = str(_DB_PATH)

    if test_config:
        app.config.update(test_config)

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    db_path = app.config.get("DB_PATH", str(_DB_PATH))
    # Ensure the data directory exists
    db_dir = Path(db_path).parent
    if str(db_dir) != ":memory:" and not db_dir.exists():
        db_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Created database directory: %s", db_dir)
    engine = get_engine(db_path=db_path)
    Base.metadata.create_all(engine)

    with get_session(engine) as db_session:
        _seed_admin(db_session)

    # ------------------------------------------------------------------
    # Register blueprints
    # ------------------------------------------------------------------
    from famicent.auth.routes import auth_bp
    from famicent.views.dashboard import dashboard_bp
    from famicent.views.accounts import accounts_bp
    from famicent.views.payments import payments_bp
    from famicent.views.settings import settings_bp
    from famicent.views.users import users_bp
    from famicent.views.dbviewer import dbviewer_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(accounts_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(dbviewer_bp)

    # ------------------------------------------------------------------
    # Security headers (R27)
    # ------------------------------------------------------------------
    @app.after_request
    def set_security_headers(response):  # type: ignore[no-untyped-def]
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:;"
        )
        return response

    return app


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    application = create_app()
    application.run(host="127.0.0.1", port=4010, debug=True)
