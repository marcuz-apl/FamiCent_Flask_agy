"""Settings view blueprint.

Provides application settings: profile info and MFA re-enrollment.
"""
from __future__ import annotations

import logging
import platform

import psutil

from flask import Blueprint, jsonify, render_template, request, session

from famicent.auth.mfa import generate_qr_base64, generate_secret, get_provisioning_uri
from famicent.auth.routes import login_required, mfa_required, admin_required, _validate_csrf
from famicent.db.engine import get_session
from famicent.db.models import User

logger = logging.getLogger(__name__)

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")


@settings_bp.route("/", methods=["GET"])
@login_required
@mfa_required
@admin_required
def index():  # type: ignore[no-untyped-def]
    """Render the settings page."""
    with get_session() as db:
        user = db.get(User, session["user_id"])
        profile_name = user.profile_name if user else ""
        session_timeout = user.session_timeout if user else 300

    return render_template(
        "settings.html",
        username=session.get("username", ""),
        profile_name=profile_name,
        session_timeout=session_timeout,
        csrf_token=session.get("csrf_token", ""),
    )


@settings_bp.route("/update-profile", methods=["POST"])
@login_required
@mfa_required
def update_profile():
    """Allow any logged-in user to update their own profile display name and timeout."""
    _validate_csrf()
    form = request.form
    new_profile_name = form.get("profile_name", "").strip() or None
    new_timeout_str = form.get("session_timeout", "").strip()

    with get_session() as db:
        user = db.get(User, session["user_id"])
        if not user:
            return jsonify({"success": False, "error": "User not found."}), 404

        user.profile_name = new_profile_name
        if new_timeout_str:
            try:
                new_timeout = int(new_timeout_str)
                if new_timeout < 60 or new_timeout > 86400:
                    return jsonify({"success": False, "error": "Timeout must be between 60 seconds (1 min) and 86400 seconds (24 hours)."}), 400
                user.session_timeout = new_timeout
                session["session_timeout"] = new_timeout # Update dynamic session value
            except ValueError:
                return jsonify({"success": False, "error": "Invalid session timeout value."}), 400

        db.commit()
        logger.info("User '%s' updated their profile details", user.username)

    return jsonify({"success": True})


@settings_bp.route("/mfa/reset", methods=["POST"])
@login_required
@mfa_required
def mfa_reset():  # type: ignore[no-untyped-def]
    """Generate a new MFA secret and return a QR code for re-enrollment."""
    _validate_csrf()
    username = session.get("username", "")
    secret = generate_secret()
    session["pending_mfa_secret"] = secret
    uri = get_provisioning_uri(secret, username)
    qr_data = generate_qr_base64(uri)
    return jsonify({"success": True, "qr_data": qr_data, "secret": secret})


@settings_bp.route("/mfa/confirm", methods=["POST"])
@login_required
@mfa_required
def mfa_confirm():  # type: ignore[no-untyped-def]
    """Confirm the new MFA secret with a valid TOTP code."""
    from famicent.auth.mfa import verify_code

    _validate_csrf()
    code = request.form.get("code", "").strip()
    secret = session.pop("pending_mfa_secret", "")

    if not secret or not verify_code(secret, code):
        return jsonify({"success": False, "error": "Invalid or expired code."}), 400

    with get_session() as db:
        user = db.get(User, session["user_id"])
        if user:
            user.mfa_secret_encrypted = secret.encode("utf-8")
            user.mfa_enabled = True
            db.commit()

    return jsonify({"success": True})


@settings_bp.route("/sysinfo", methods=["GET"])
@login_required
@mfa_required
def sysinfo() -> "flask.Response":  # type: ignore[name-defined]
    """Return live CPU, RAM, and GPU statistics as JSON.

    GPU info is collected via optional GPUtil. Falls back gracefully when
    no NVIDIA GPU or GPUtil is not installed.
    """
    # ── CPU ─────────────────────────────────────────────────────────
    cpu_freq = psutil.cpu_freq()
    cpu_info = {
        "name": platform.processor() or "Unknown CPU",
        "physical_cores": psutil.cpu_count(logical=False) or 1,
        "logical_cores": psutil.cpu_count(logical=True) or 1,
        "freq_mhz": round(cpu_freq.current, 0) if cpu_freq else None,
        "freq_max_mhz": round(cpu_freq.max, 0) if cpu_freq else None,
        "usage_total": psutil.cpu_percent(interval=0.1),
        "usage_per_core": psutil.cpu_percent(interval=0.1, percpu=True),
    }

    # ── RAM ─────────────────────────────────────────────────────────
    vm = psutil.virtual_memory()
    ram_info = {
        "total_gb": round(vm.total / (1024 ** 3), 2),
        "available_gb": round(vm.available / (1024 ** 3), 2),
        "used_gb": round(vm.used / (1024 ** 3), 2),
        "percent": vm.percent,
    }

    # ── GPU ─────────────────────────────────────────────────────────
    gpus: list[dict] = []
    try:
        import GPUtil  # type: ignore[import-untyped]
        for g in GPUtil.getGPUs():
            gpus.append({
                "name": g.name,
                "load_percent": round(g.load * 100, 1),
                "mem_total_mb": round(g.memoryTotal, 0),
                "mem_used_mb": round(g.memoryUsed, 0),
                "mem_free_mb": round(g.memoryFree, 0),
                "mem_percent": round(g.memoryUsed / g.memoryTotal * 100, 1) if g.memoryTotal else 0,
                "temperature_c": g.temperature,
            })
    except Exception:
        gpus = []

    return jsonify({"cpu": cpu_info, "ram": ram_info, "gpus": gpus})

