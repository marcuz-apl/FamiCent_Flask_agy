"""Payment business-logic service.

Provides CRUD operations for payments and helpers for upcoming-payment queries.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from famicent.db.models import Account, Payment, PaymentMethod

logger = logging.getLogger(__name__)


def record_payment(
    db: Session,
    *,
    account_id: str,
    amount: float,
    payment_date: datetime,
    method: str = PaymentMethod.BANK_TRANSFER.value,
    reference_number_encrypted: bytes | None = None,
    creator_user_id: str | None = None,
) -> Payment:
    """Record a new payment against an account.

    Args:
        db: An active database session.
        account_id: The account being paid.
        amount: Payment amount.
        payment_date: When the payment was made.
        method: One of PaymentMethod values.
        reference_number_encrypted: Encrypted reference number bytes.
        creator_user_id: The user recording this payment.

    Returns:
        The newly created Payment instance.
    """
    payment = Payment(
        account_id=account_id,
        amount=amount,
        payment_date=payment_date,
        method=method,
        reference_number_encrypted=reference_number_encrypted,
        creator_user_id=creator_user_id,
        editor_user_id=creator_user_id,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    logger.info(
        "Recorded payment of %.2f for account %s by user %s", amount, account_id, creator_user_id
    )
    return payment


def get_payment(db: Session, payment_id: str) -> Payment | None:
    """Fetch a single payment by ID.

    Args:
        db: An active database session.
        payment_id: The payment's UUID string.

    Returns:
        The Payment or None if not found.
    """
    stmt = select(Payment).where(Payment.id == payment_id)
    return db.execute(stmt).scalar_one_or_none()


def list_payments(
    db: Session,
    account_id: str | None = None,
    user_id: str | None = None,
    limit: int = 50,
) -> list[Payment]:
    """List payments, optionally filtered by account or user.

    Args:
        db: An active database session.
        account_id: Optional filter by specific account.
        user_id: Optional filter by user (via account ownership).
        limit: Maximum number of results.

    Returns:
        A list of Payment instances, newest first.
    """
    stmt = select(Payment)
    if account_id:
        stmt = stmt.where(Payment.account_id == account_id)
    elif user_id:
        stmt = stmt.join(Account).where(Account.user_id == user_id)
    stmt = stmt.order_by(Payment.payment_date.desc()).limit(limit)
    return list(db.execute(stmt).scalars().all())


def delete_payment(db: Session, payment_id: str) -> bool:
    """Delete a payment record.

    Args:
        db: An active database session.
        payment_id: The payment's UUID string.

    Returns:
        True if deleted, False if not found.
    """
    payment = get_payment(db, payment_id)
    if payment is None:
        return False
    db.delete(payment)
    db.commit()
    logger.info("Deleted payment %s", payment_id)
    return True


def update_payment(
    db: Session,
    payment_id: str,
    editor_user_id: str | None = None,
    **fields: object
) -> Payment | None:
    """Update fields on an existing payment.

    Args:
        db: An active database session.
        payment_id: The payment's UUID string.
        editor_user_id: The user performing the update.
        **fields: Keyword arguments of column names to new values.

    Returns:
        The updated Payment, or None if not found.
    """
    payment = get_payment(db, payment_id)
    if payment is None:
        return None
    for key, value in fields.items():
        if hasattr(payment, key):
            setattr(payment, key, value)
    if editor_user_id:
        payment.editor_user_id = editor_user_id
    payment.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(payment)
    logger.info("Updated payment %s", payment_id)
    return payment


def get_upcoming_payments(
    db: Session, user_id: str, days: int = 30, fetch_all: bool = False
) -> list[Account]:
    """Find accounts with due dates within the next N days.

    Args:
        db: An active database session.
        user_id: The user whose accounts to check.
        days: Look-ahead window in days (default 30).
        fetch_all: If True, search across all users.

    Returns:
        A list of Account instances with upcoming due dates, sorted by date.
    """
    cutoff = datetime.utcnow() + timedelta(days=days)
    stmt = select(Account)
    if not fetch_all:
        stmt = stmt.where(Account.user_id == user_id)
    stmt = (
        stmt.where(Account.next_due_date.isnot(None))
        .where(Account.next_due_date <= cutoff)
        .order_by(Account.next_due_date.asc())
    )
    return list(db.execute(stmt).scalars().all())


def get_total_outstanding(db: Session, user_id: str, fetch_all: bool = False) -> float:
    """Sum the balances of all accounts.

    Args:
        db: An active database session.
        user_id: The user's ID.
        fetch_all: If True, aggregate across all users.

    Returns:
        Total outstanding balance as a float.
    """
    stmt = select(func.coalesce(func.sum(Account.balance), 0.0))
    if not fetch_all:
        stmt = stmt.where(Account.user_id == user_id)
    result = db.execute(stmt).scalar()
    return float(result) if result else 0.0


def get_monthly_spending(
    db: Session, user_id: str, year: int, month: int, fetch_all: bool = False
) -> float:
    """Sum all payments in a given month.

    Args:
        db: An active database session.
        user_id: The user's ID.
        year: The year (e.g. 2026).
        month: The month (1-12).
        fetch_all: If True, aggregate across all users.

    Returns:
        Total payment amount for the month.
    """
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)

    stmt = select(func.coalesce(func.sum(Payment.amount), 0.0)).join(Account)
    if not fetch_all:
        stmt = stmt.where(Account.user_id == user_id)
    stmt = (
        stmt.where(Payment.payment_date >= start)
        .where(Payment.payment_date < end)
    )
    result = db.execute(stmt).scalar()
    return float(result) if result else 0.0
