"""Users management view blueprint.

Allows admins to manage family user accounts. Max 5 non-admin users (editors/viewers).
"""
from __future__ import annotations

import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, abort
from sqlalchemy import select, func
from famicent.auth.routes import login_required, mfa_required, admin_required, _validate_csrf
from famicent.auth.manager import hash_password
from famicent.db.engine import get_session
from famicent.db.models import User, UserRole

logger = logging.getLogger(__name__)

users_bp = Blueprint("users", __name__, url_prefix="/users")

@users_bp.route("/", methods=["GET"])
@login_required
@mfa_required
@admin_required
def index():
    """List all users."""
    with get_session() as db:
        stmt = select(User).order_by(User.username)
        users_list = db.execute(stmt).scalars().all()
        # Count non-admin users
        non_admin_count = sum(1 for u in users_list if u.role != UserRole.ADMIN)

    return render_template(
        "users.html",
        users=users_list,
        roles=[r.value for r in UserRole],
        non_admin_count=non_admin_count,
        csrf_token=session.get("csrf_token", ""),
    )

@users_bp.route("/create", methods=["POST"])
@login_required
@mfa_required
@admin_required
def create():
    """Create a new user."""
    _validate_csrf()
    form = request.form
    username = form.get("username", "").strip().lower()
    password = form.get("password", "")
    role = form.get("role", UserRole.VIEWER.value)
    profile_name = form.get("profile_name", "").strip() or None

    if not username or not password:
        return jsonify({"success": False, "error": "Username and password are required."}), 400

    if role == UserRole.ADMIN.value:
        return jsonify({"success": False, "error": "Cannot create additional admin users."}), 400

    with get_session() as db:
        # Check maximum 5 non-admin users limit
        non_admin_stmt = select(func.count(User.id)).where(User.role != UserRole.ADMIN)
        non_admin_count = db.execute(non_admin_stmt).scalar() or 0
        if non_admin_count >= 5:
            return jsonify({"success": False, "error": "Maximum of 5 family members (editors/viewers) allowed."}), 400

        # Check unique username
        dup_stmt = select(User).where(User.username == username)
        if db.execute(dup_stmt).scalar_one_or_none() is not None:
            return jsonify({"success": False, "error": "Username already exists."}), 400

        mfa_enforced = (form.get("mfa_enforced") == "true")

        new_user = User(
            username=username,
            role=role,
            password_hash=hash_password(password).encode("utf-8"),
            profile_name=profile_name,
            password_changed=True,  # They start with a set password, not default
            mfa_enabled=False,
            mfa_enforced=mfa_enforced,
        )
        db.add(new_user)
        db.commit()
        logger.info("Admin created new user '%s' with role '%s', mfa_enforced=%s", username, role, mfa_enforced)

    return jsonify({"success": True})

@users_bp.route("/<user_id>/delete", methods=["POST"])
@login_required
@mfa_required
@admin_required
def delete(user_id: str):
    """Delete a user."""
    _validate_csrf()
    if user_id == session.get("user_id"):
        return jsonify({"success": False, "error": "Cannot delete yourself."}), 400

    with get_session() as db:
        user = db.get(User, user_id)
        if not user:
            abort(404)
        if user.role == UserRole.ADMIN:
            return jsonify({"success": False, "error": "Cannot delete admin users."}), 400
        db.delete(user)
        db.commit()
        logger.info("Admin deleted user '%s'", user.username)

    return jsonify({"success": True})

@users_bp.route("/<user_id>/update", methods=["POST"])
@login_required
@mfa_required
@admin_required
def update(user_id: str):
    """Admin updates another user's profile and/or resets their password."""
    _validate_csrf()
    form = request.form
    new_profile_name = form.get("profile_name", "").strip() or None
    new_password = form.get("password", "").strip()
    new_role = form.get("role", "").strip()
    new_timeout_str = form.get("session_timeout", "").strip()

    with get_session() as db:
        user = db.get(User, user_id)
        if not user:
            abort(404)

        user.profile_name = new_profile_name
        if new_password:
            if len(new_password) < 8:
                return jsonify({"success": False, "error": "Password must be at least 8 characters."}), 400
            user.password_hash = hash_password(new_password).encode("utf-8")
        
        # Prevent demoting the superadmin role
        if user.role != UserRole.ADMIN:
            if new_role in (UserRole.EDITOR.value, UserRole.VIEWER.value):
                user.role = new_role

        if new_timeout_str:
            try:
                new_timeout = int(new_timeout_str)
                # Enforce bounds: min 60 seconds (1 min), max 86400 seconds (24 hours)
                if new_timeout < 60 or new_timeout > 86400:
                    return jsonify({"success": False, "error": "Timeout must be between 60 seconds (1 min) and 86400 seconds (24 hours)."}), 400
                user.session_timeout = new_timeout
            except ValueError:
                return jsonify({"success": False, "error": "Invalid session timeout value."}), 400

        # Save MFA enforcement status
        user.mfa_enforced = (form.get("mfa_enforced") == "true")

        # If admin requests to reset MFA (forcing them to re-enroll next login)
        if form.get("reset_mfa") == "true":
            user.mfa_enabled = False
            user.mfa_secret_encrypted = None
            logger.info("Admin reset MFA configuration for user '%s'", user.username)

        db.commit()
        logger.info("Admin updated profile/password/role/timeout/mfa for user '%s'", user.username)

    return jsonify({"success": True})

@users_bp.route("/<user_id>", methods=["GET"])
@login_required
@mfa_required
@admin_required
def detail(user_id: str):
    """Fetch user profile details (used by edit modals)."""
    with get_session() as db:
        user = db.get(User, user_id)
    if not user:
        abort(404)
    return jsonify({
        "id": user.id,
        "username": user.username,
        "profile_name": user.profile_name or "",
        "role": user.role,
        "mfa_enabled": user.mfa_enabled,
        "mfa_enforced": user.mfa_enforced,
        "session_timeout": user.session_timeout,
    })
