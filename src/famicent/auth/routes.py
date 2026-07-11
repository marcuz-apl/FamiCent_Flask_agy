"""Authentication routes for FamiCent.

Handles login (password check), MFA verification, MFA enrollment, logout,
password change (manual and generated), and CSRF token injection.
"""
from __future__ import annotations

import logging
import secrets
from datetime import datetime
from functools import wraps
from typing import Any

from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy import select

from famicent.auth.manager import hash_password, is_session_expired, verify_password
from famicent.auth.mfa import (
    generate_qr_base64,
    generate_secret,
    get_provisioning_uri,
    verify_code,
)
from famicent.db.engine import get_session
from famicent.db.models import User
from famicent.utils.helpers import SESSION_TIMEOUT_SECONDS, generate_secure_password

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)

# ---------------------------------------------------------------------------
# CSRF helpers
# ---------------------------------------------------------------------------

def _generate_csrf() -> str:
    """Generate and store a CSRF token in the Flask session."""
    token = secrets.token_hex(32)
    session["csrf_token"] = token
    return token


def _validate_csrf() -> None:
    """Validate the CSRF token on POST requests; abort 403 if invalid."""
    if request.method != "POST":
        return
    token = session.get("csrf_token", "")
    submitted = request.form.get("csrf_token", "")
    if not secrets.compare_digest(token, submitted):
        logger.warning("CSRF validation failed from %s", request.remote_addr)
        abort(403)


# ---------------------------------------------------------------------------
# Auth decorators
# ---------------------------------------------------------------------------

def login_required(f):  # type: ignore[no-untyped-def]
    """Redirect to login if user is not authenticated or session is expired."""
    @wraps(f)
    def decorated(*args: Any, **kwargs: Any):  # type: ignore[no-untyped-def]
        user_id = session.get("user_id")
        last_activity = session.get("last_activity")
        timeout_seconds = session.get("session_timeout", 300) # Fallback to 5 minutes
        if not user_id:
            return redirect(url_for("auth.login"))
        if last_activity and is_session_expired(
            datetime.fromisoformat(last_activity),
            timeout_seconds=timeout_seconds
        ):
            session.clear()
            flash("Session expired. Please log in again.", "warning")
            return redirect(url_for("auth.login"))
        # Refresh activity timestamp
        session["last_activity"] = datetime.utcnow().isoformat()
        return f(*args, **kwargs)

    return decorated


def mfa_required(f):  # type: ignore[no-untyped-def]
    """Redirect to MFA verification if MFA is required (either enabled or enforced)."""
    @wraps(f)
    def decorated(*args: Any, **kwargs: Any):  # type: ignore[no-untyped-def]
        # Bypasses check if session indicates verification completed
        if session.get("mfa_verified"):
            return f(*args, **kwargs)

        # Check if user has MFA setup or if the admin enforces it
        user_id = session.get("user_id") or session.get("pending_user_id")
        if user_id:
            with get_session() as db:
                user = db.get(User, user_id)
                if user:
                    # If not enabled and not enforced, bypass MFA redirect
                    if not user.mfa_enabled and not user.mfa_enforced:
                        session["mfa_verified"] = True
                        return f(*args, **kwargs)

        if not session.get("mfa_verified"):
            return redirect(url_for("auth.mfa_verify"))
        return f(*args, **kwargs)

    return decorated


def admin_required(f):  # type: ignore[no-untyped-def]
    """Gives access only if logged in user is admin."""
    @wraps(f)
    def decorated(*args: Any, **kwargs: Any):  # type: ignore[no-untyped-def]
        if session.get("role") != "admin":
            flash("Administrator permissions required.", "error")
            return redirect(url_for("dashboard.index"))
        return f(*args, **kwargs)

    return decorated


def editor_required(f):  # type: ignore[no-untyped-def]
    """Gives access if user is admin or editor (can modify records)."""
    @wraps(f)
    def decorated(*args: Any, **kwargs: Any):  # type: ignore[no-untyped-def]
        if session.get("role") not in ("admin", "editor"):
            if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json or request.path.endswith("/delete") or request.path.endswith("/create") or request.path.endswith("/update") or request.path.endswith("/record"):
                return jsonify({"success": False, "error": "Insufficient permissions to perform this action."}), 403
            flash("You do not have permission to perform this action.", "error")
            return redirect(url_for("dashboard.index"))
        return f(*args, **kwargs)

    return decorated



# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@auth_bp.route("/", methods=["GET"])
def index():  # type: ignore[no-untyped-def]
    """Redirect root to dashboard or login."""
    if session.get("user_id") and session.get("mfa_verified"):
        return redirect(url_for("dashboard.index"))
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():  # type: ignore[no-untyped-def]
    """Handle username/password login (Step 1 of 2-factor auth)."""
    if request.method == "POST":
        _validate_csrf()
        csrf_token = session.get("csrf_token", "")
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user_id: str | None = None
        user_name: str | None = None
        user_role: str | None = None
        user_mfa_enabled: bool = False
        user_password_changed: bool = False
        user_session_timeout: int = 300
        user_mfa_enforced: bool = False
        stored_hash: str | None = None

        with get_session() as db:
            user = db.execute(
                select(User).where(User.username == username)
            ).scalar_one_or_none()
            if user is not None:
                user_id = user.id
                user_name = user.username
                user_role = user.role
                user_mfa_enabled = user.mfa_enabled
                user_mfa_enforced = user.mfa_enforced
                user_password_changed = user.password_changed
                user_session_timeout = user.session_timeout
                stored_hash = (
                    user.password_hash.decode("utf-8")
                    if isinstance(user.password_hash, bytes)
                    else user.password_hash
                )

        if stored_hash is None or not verify_password(stored_hash, password):
            flash("Invalid username or password.", "error")
            return render_template("login.html", csrf_token=csrf_token)

        # Store user identity pending MFA verification
        session.clear()
        session["pending_user_id"] = user_id
        session["pending_username"] = user_name
        session["pending_role"] = user_role
        session["pending_mfa_enabled"] = user_mfa_enabled
        session["pending_mfa_enforced"] = user_mfa_enforced
        session["pending_password_changed"] = user_password_changed
        session["pending_session_timeout"] = user_session_timeout
        session["last_activity"] = datetime.utcnow().isoformat()
        _generate_csrf()  # fresh token for the next page (MFA)

        # Bypasses MFA if not active and not enforced
        if not user_mfa_enabled and not user_mfa_enforced:
            return _complete_login()

        if user_mfa_enabled:
            return redirect(url_for("auth.mfa_verify"))

        # MFA not enrolled yet, but admin enforces it → go to MFA setup
        return redirect(url_for("auth.mfa_setup"))

    # GET
    csrf_token = _generate_csrf()
    return render_template("login.html", csrf_token=csrf_token)


@auth_bp.route("/mfa/setup", methods=["GET", "POST"])
def mfa_setup():  # type: ignore[no-untyped-def]
    """First-time MFA enrollment: show QR code and verify initial code."""
    if not session.get("pending_user_id"):
        return redirect(url_for("auth.login"))

    username = session.get("pending_username", "")

    if request.method == "GET":
        csrf_token = _generate_csrf()
        secret = generate_secret()
        session["pending_mfa_secret"] = secret
        uri = get_provisioning_uri(secret, username)
        qr_data = generate_qr_base64(uri)
        return render_template(
            "mfa.html",
            mode="setup",
            qr_data=qr_data,
            secret=secret,
            csrf_token=csrf_token,
        )

    # POST: verify submitted code and save secret
    _validate_csrf()
    csrf_token = session.get("csrf_token", "")
    code = request.form.get("code", "").strip()
    secret = session.get("pending_mfa_secret", "")

    if not verify_code(secret, code):
        flash("Invalid code. Please try again.", "error")
        uri = get_provisioning_uri(secret, username)
        qr_data = generate_qr_base64(uri)
        return render_template(
            "mfa.html",
            mode="setup",
            qr_data=qr_data,
            secret=secret,
            csrf_token=csrf_token,
        )

    # Persist the MFA secret on the user record
    with get_session() as db:
        user = db.get(User, session["pending_user_id"])
        if user:
            user.mfa_secret_encrypted = secret.encode("utf-8")
            user.mfa_enabled = True
            db.commit()

    return _complete_login()


@auth_bp.route("/mfa/verify", methods=["GET", "POST"])
def mfa_verify():  # type: ignore[no-untyped-def]
    """TOTP code verification for users who already enrolled MFA."""
    if not session.get("pending_user_id"):
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        _validate_csrf()
        csrf_token = session.get("csrf_token", "")
        code = request.form.get("code", "").strip()

        with get_session() as db:
            user = db.get(User, session["pending_user_id"])

        if user is None or not user.mfa_secret_encrypted:
            flash("MFA not configured. Please log in again.", "error")
            return redirect(url_for("auth.login"))

        secret = user.mfa_secret_encrypted.decode("utf-8")
        if not verify_code(secret, code):
            flash("Invalid or expired code. Please try again.", "error")
            return render_template("mfa.html", mode="verify", csrf_token=csrf_token)

        return _complete_login()

    # GET — generate fresh token for the verify form
    csrf_token = _generate_csrf()
    return render_template("mfa.html", mode="verify", csrf_token=csrf_token)


def _complete_login():  # type: ignore[no-untyped-def]
    """Finalise the login: promote pending session to authenticated."""
    session["user_id"] = session.pop("pending_user_id")
    session["username"] = session.pop("pending_username")
    session["role"] = session.pop("pending_role")
    session["password_changed"] = session.pop("pending_password_changed", False)
    session["session_timeout"] = session.pop("pending_session_timeout", 300)
    session["mfa_verified"] = True
    session.pop("pending_mfa_secret", None)
    session.pop("pending_mfa_enabled", None)
    logger.info("User '%s' logged in successfully.", session["username"])
    return redirect(url_for("dashboard.index"))


@auth_bp.route("/logout", methods=["POST"])
def logout():  # type: ignore[no-untyped-def]
    """Clear the session and redirect to login."""
    _validate_csrf()
    username = session.get("username", "unknown")
    session.clear()
    logger.info("User '%s' logged out.", username)
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/change-password", methods=["POST"])
@login_required
@mfa_required
def change_password():  # type: ignore[no-untyped-def]
    """Handle manual password change (FR-USR-MGT-03 / R42)."""
    _validate_csrf()
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    if len(new_password) < 8:
        return jsonify({"success": False, "error": "Password must be at least 8 characters."}), 400
    if new_password != confirm_password:
        return jsonify({"success": False, "error": "Passwords do not match."}), 400

    with get_session() as db:
        user = db.get(User, session["user_id"])
        if user:
            user.password_hash = hash_password(new_password).encode("utf-8")
            user.password_changed = True
            db.commit()

    session["password_changed"] = True
    return jsonify({"success": True})


@auth_bp.route("/generate-password", methods=["POST"])
@login_required
@mfa_required
def generate_password():  # type: ignore[no-untyped-def]
    """Generate a secure random password and apply it (FR-USR-MGT-03 / R43)."""
    _validate_csrf()
    new_password = generate_secure_password()

    with get_session() as db:
        user = db.get(User, session["user_id"])
        if user:
            user.password_hash = hash_password(new_password).encode("utf-8")
            user.password_changed = True
            db.commit()

    session["password_changed"] = True
    return jsonify({"success": True, "password": new_password})
