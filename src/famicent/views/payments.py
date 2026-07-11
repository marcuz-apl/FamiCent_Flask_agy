"""Payments view blueprint.

Handles recording payments, listing history, and payment deletion.
"""
from __future__ import annotations

import logging
from datetime import datetime

from flask import (
    Blueprint,
    abort,
    jsonify,
    render_template,
    request,
    session,
)

from famicent.auth.routes import login_required, mfa_required, editor_required, _validate_csrf
from famicent.db.engine import get_session
from famicent.db.models import PaymentMethod
from famicent.services.account_svc import get_account, list_accounts
from famicent.services.payment_svc import (
    delete_payment,
    list_payments,
    record_payment,
)
from famicent.utils.helpers import format_currency, format_date

logger = logging.getLogger(__name__)

payments_bp = Blueprint("payments", __name__, url_prefix="/payments")


@payments_bp.route("/", methods=["GET"])
@login_required
@mfa_required
def index():  # type: ignore[no-untyped-def]
    """Render the payment history page (FR-PAY-03)."""
    user_id = session["user_id"]
    account_filter = request.args.get("account_id")

    role = session.get("role")
    fetch_all = role in ("editor", "viewer", "admin")

    with get_session() as db:
        accounts = list_accounts(db, user_id, fetch_all=fetch_all)
        # If fetch_all is active, pass user_id=None to service to get all records, else pass user_id
        payments = list_payments(
            db,
            account_id=account_filter,
            user_id=None if fetch_all else user_id,
            limit=100
        )

    # Build account lookup map for display
    account_map = {a.id: a.name for a in accounts}

    return render_template(
        "payments.html",
        payments=payments,
        accounts=accounts,
        account_map=account_map,
        account_filter=account_filter or "",
        payment_methods=[m.value for m in PaymentMethod],
        format_currency=format_currency,
        format_date=format_date,
        csrf_token=session.get("csrf_token", ""),
    )


@payments_bp.route("/record", methods=["POST"])
@login_required
@mfa_required
@editor_required
def record():  # type: ignore[no-untyped-def]
    """Record a new payment against an account (FR-PAY-01)."""
    _validate_csrf()
    form = request.form

    account_id = form.get("account_id", "").strip()
    amount_str = form.get("amount", "0").strip()
    date_str = form.get("payment_date", "").strip()
    method = form.get("method", PaymentMethod.BANK_TRANSFER.value)

    # Validate account existence
    with get_session() as db:
        account = get_account(db, account_id)
    if account is None:
        return jsonify({"success": False, "error": "Account not found."}), 404

    try:
        amount = float(amount_str)
    except ValueError:
        return jsonify({"success": False, "error": "Invalid amount."}), 400

    try:
        payment_date = datetime.strptime(date_str, "%Y-%m-%d") if date_str else datetime.utcnow()
    except ValueError:
        return jsonify({"success": False, "error": "Invalid payment date."}), 400

    with get_session() as db:
        payment = record_payment(
            db,
            account_id=account_id,
            amount=amount,
            payment_date=payment_date,
            method=method.lower(),
            creator_user_id=session["user_id"],
        )

    return jsonify({"success": True, "payment_id": payment.id})


@payments_bp.route("/<payment_id>", methods=["GET"])
@login_required
@mfa_required
def detail(payment_id: str):  # type: ignore[no-untyped-def]
    """Get payment details as JSON."""
    from famicent.services.payment_svc import get_payment
    with get_session() as db:
        payment = get_payment(db, payment_id)
    if payment is None:
        abort(404)
    return jsonify({
        "id": payment.id,
        "account_id": payment.account_id,
        "amount": payment.amount,
        "payment_date": payment.payment_date.strftime("%Y-%m-%d"),
        "method": payment.method,
    })


@payments_bp.route("/<payment_id>/update", methods=["POST"])
@login_required
@mfa_required
@editor_required
def update(payment_id: str):  # type: ignore[no-untyped-def]
    """Update an existing payment."""
    _validate_csrf()
    from famicent.services.payment_svc import get_payment, update_payment
    with get_session() as db:
        payment = get_payment(db, payment_id)
        if payment is None:
            abort(404)

    form = request.form
    account_id = form.get("account_id", "").strip()
    amount_str = form.get("amount", "0").strip()
    date_str = form.get("payment_date", "").strip()
    method = form.get("method", PaymentMethod.BANK_TRANSFER.value)

    # Validate account existence
    with get_session() as db:
        account = get_account(db, account_id)
    if account is None:
        return jsonify({"success": False, "error": "Account not found."}), 404

    try:
        amount = float(amount_str)
    except ValueError:
        return jsonify({"success": False, "error": "Invalid amount."}), 400

    try:
        payment_date = datetime.strptime(date_str, "%Y-%m-%d") if date_str else datetime.utcnow()
    except ValueError:
        return jsonify({"success": False, "error": "Invalid payment date."}), 400

    with get_session() as db:
        update_payment(
            db,
            payment_id,
            editor_user_id=session["user_id"],
            account_id=account_id,
            amount=amount,
            payment_date=payment_date,
            method=method.lower(),
        )

    return jsonify({"success": True})


@payments_bp.route("/<payment_id>/delete", methods=["POST"])
@login_required
@mfa_required
@editor_required
def delete(payment_id: str):  # type: ignore[no-untyped-def]
    """Delete a payment record."""
    _validate_csrf()

    with get_session() as db:
        from famicent.services.payment_svc import get_payment
        payment = get_payment(db, payment_id)
        if payment is None:
            abort(404)
        delete_payment(db, payment_id)

    return jsonify({"success": True})
