"""Accounts view blueprint.

Handles CRUD operations for financial accounts via web forms and JSON endpoints.
"""
from __future__ import annotations

import logging
import secrets
from datetime import datetime

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

from famicent.auth.routes import login_required, mfa_required, editor_required, _validate_csrf
from famicent.db.engine import get_session
from famicent.db.models import AccountCategory, BillingCycle
from famicent.services.account_svc import (
    create_account,
    delete_account,
    get_account,
    list_accounts,
    update_account,
)
from famicent.utils.helpers import format_currency, format_date

logger = logging.getLogger(__name__)

accounts_bp = Blueprint("accounts", __name__, url_prefix="/accounts")


@accounts_bp.route("/", methods=["GET"])
@login_required
@mfa_required
def index():  # type: ignore[no-untyped-def]
    """List all accounts for the current user."""
    user_id = session["user_id"]
    category_filter = request.args.get("category")
    role = session.get("role")
    fetch_all = role in ("editor", "viewer", "admin")

    with get_session() as db:
        accounts = list_accounts(db, user_id, category=category_filter, fetch_all=fetch_all)

    return render_template(
        "accounts.html",
        accounts=accounts,
        categories=[c.value for c in AccountCategory],
        billing_cycles=[c.value for c in BillingCycle],
        category_filter=category_filter,
        format_currency=format_currency,
        format_date=format_date,
        csrf_token=session.get("csrf_token", ""),
    )


@accounts_bp.route("/create", methods=["POST"])
@login_required
@mfa_required
@editor_required
def create():  # type: ignore[no-untyped-def]
    """Create a new account from form data."""
    _validate_csrf()
    user_id = session["user_id"]
    form = request.form

    billing_cycle = form.get("billing_cycle", BillingCycle.MONTHLY.value).lower()
    next_due_str = form.get("next_due_date", "").strip()
    next_due: str | None = None
    if next_due_str:
        if billing_cycle == "weekly":
            # Weekday integers '1'-'7' are acceptable raw strings
            next_due = next_due_str
        elif billing_cycle == "monthly":
            # Monthly cycles can have dates in format "MM-DD" or "YYYY-MM-DD"
            next_due = next_due_str
        else:
            try:
                # Validate full YYYY-MM-DD formatting for standard dates
                dt = datetime.strptime(next_due_str, "%Y-%m-%d")
                next_due = dt.strftime("%Y-%m-%d")
            except ValueError:
                return jsonify({"success": False, "error": "Invalid due date format."}), 400

    with get_session() as db:
        account = create_account(
            db,
            user_id=user_id,
            name=form.get("name", "").strip(),
            category=form.get("category", AccountCategory.CUSTOM.value).lower(),
            provider=form.get("provider", "").strip() or None,
            balance=float(form.get("balance", 0) or 0),
            billing_cycle=form.get("billing_cycle", BillingCycle.MONTHLY.value).lower(),
            next_due_date=next_due,
            creator_user_id=user_id,
            website_url=form.get("website_url", "").strip() or None,
            website_username=form.get("website_username", "").strip() or None,
            website_password=form.get("website_password", "").strip() or None,
            notes=form.get("notes", "").strip() or None,
        )

    return jsonify({"success": True, "account_id": account.id})


@accounts_bp.route("/<account_id>", methods=["GET"])
@login_required
@mfa_required
def detail(account_id: str):  # type: ignore[no-untyped-def]
    """Get account details as JSON (used by the modal)."""
    with get_session() as db:
        account = get_account(db, account_id)
    if account is None:
        abort(404)
    return jsonify({
        "id": account.id,
        "name": account.name,
        "category": account.category,
        "provider": account.provider or "",
        "balance": account.balance,
        "billing_cycle": account.billing_cycle,
        "next_due_date": account.next_due_date or "",
        "website_url": account.website_url or "",
        "website_username": account.website_username or "",
        "website_password": account.website_password or "",
        "notes": account.notes or "",
    })


@accounts_bp.route("/<account_id>/update", methods=["POST"])
@login_required
@mfa_required
@editor_required
def update(account_id: str):  # type: ignore[no-untyped-def]
    """Update an existing account."""
    _validate_csrf()

    with get_session() as db:
        account = get_account(db, account_id)
        if account is None:
            abort(404)

    form = request.form
    billing_cycle = form.get("billing_cycle", BillingCycle.MONTHLY.value).lower()
    next_due_str = form.get("next_due_date", "").strip()
    next_due: str | None = None
    if next_due_str:
        if billing_cycle == "weekly":
            next_due = next_due_str
        elif billing_cycle == "monthly":
            next_due = next_due_str
        else:
            try:
                dt = datetime.strptime(next_due_str, "%Y-%m-%d")
                next_due = dt.strftime("%Y-%m-%d")
            except ValueError:
                return jsonify({"success": False, "error": "Invalid due date format."}), 400

    with get_session() as db:
        update_account(
            db,
            account_id,
            editor_user_id=session["user_id"],
            name=form.get("name", "").strip(),
            category=form.get("category", AccountCategory.CUSTOM.value).lower(),
            provider=form.get("provider", "").strip() or None,
            balance=float(form.get("balance", 0) or 0),
            billing_cycle=form.get("billing_cycle", BillingCycle.MONTHLY.value).lower(),
            next_due_date=next_due,
            website_url=form.get("website_url", "").strip() or None,
            website_username=form.get("website_username", "").strip() or None,
            website_password=form.get("website_password", "").strip() or None,
            notes=form.get("notes", "").strip() or None,
        )

    return jsonify({"success": True})


@accounts_bp.route("/<account_id>/delete", methods=["POST"])
@login_required
@mfa_required
@editor_required
def delete(account_id: str):  # type: ignore[no-untyped-def]
    """Delete an account and all related records."""
    _validate_csrf()

    with get_session() as db:
        account = get_account(db, account_id)
        if account is None:
            abort(404)
        delete_account(db, account_id)

    return jsonify({"success": True})
