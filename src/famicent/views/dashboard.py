"""Dashboard view blueprint.

Renders the main dashboard with account summary, upcoming payments,
and monthly spending totals.
"""
from __future__ import annotations

import logging
from datetime import datetime

from flask import Blueprint, render_template, session

from famicent.auth.routes import login_required, mfa_required
from famicent.db.engine import get_session
from famicent.services.account_svc import list_accounts
from famicent.services.payment_svc import (
    get_monthly_spending,
    get_total_outstanding,
    get_upcoming_payments,
    list_payments,
)
from famicent.utils.helpers import format_currency, format_date

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
@mfa_required
def index():  # type: ignore[no-untyped-def]
    """Render the main dashboard (FR-DASH-01)."""
    user_id = session["user_id"]
    now = datetime.utcnow()

    role = session.get("role")
    fetch_all = role in ("editor", "viewer", "admin")

    with get_session() as db:
        accounts = list_accounts(db, user_id, fetch_all=fetch_all)
        upcoming = get_upcoming_payments(db, user_id, days=30, fetch_all=fetch_all)
        total_outstanding = get_total_outstanding(db, user_id, fetch_all=fetch_all)
        monthly_spending = get_monthly_spending(db, user_id, now.year, now.month, fetch_all=fetch_all)
        recent_payments = list_payments(db, user_id=None if fetch_all else user_id, limit=5)

    # Group accounts by category for display
    accounts_by_category: dict[str, list] = {}
    for acc in accounts:
        cat = acc.category
        accounts_by_category.setdefault(cat, []).append(acc)

    show_password_banner = (
        session.get("role") == "admin"
        and not session.get("password_changed", False)
    )

    return render_template(
        "dashboard.html",
        accounts=accounts,
        accounts_by_category=accounts_by_category,
        upcoming=upcoming,
        total_outstanding=format_currency(total_outstanding),
        monthly_spending=format_currency(monthly_spending),
        recent_payments=recent_payments,
        show_password_banner=show_password_banner,
        format_date=format_date,
        format_currency=format_currency,
        now=now,
    )
