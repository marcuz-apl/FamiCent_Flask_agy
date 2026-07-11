"""Account business-logic service.

Provides CRUD operations for financial accounts. Views call these functions
instead of touching the DB layer directly.
"""
from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from famicent.db.models import Account, AccountCategory, BillingCycle

logger = logging.getLogger(__name__)


def create_account(
    db: Session,
    *,
    user_id: str,
    name: str,
    category: str,
    provider: str | None = None,
    account_number_encrypted: bytes | None = None,
    balance: float = 0.0,
    credit_limit: float | None = None,
    interest_rate: float | None = None,
    billing_cycle: str = BillingCycle.MONTHLY.value,
    next_due_date: str | None = None,
    notes_encrypted: bytes | None = None,
    creator_user_id: str | None = None,
    notes: str | None = None,
    website_url: str | None = None,
    website_username: str | None = None,
    website_password: str | None = None,
) -> Account:
    """Create and persist a new financial account.

    Args:
        db: An active database session.
        user_id: The owning user's ID.
        name: Display name for the account.
        category: One of AccountCategory values.
        provider: The service provider name.
        account_number_encrypted: Encrypted account number bytes.
        balance: Current balance or amount owed.
        credit_limit: Credit limit (for credit cards).
        interest_rate: Annual interest rate percentage.
        billing_cycle: One of BillingCycle values.
        next_due_date: When the next payment is due.
        notes_encrypted: Encrypted notes bytes.
        creator_user_id: The user recording this account.
        website_url: External payment website link.
        website_username: External website login username.
        website_password: External website login password.
        notes: Plain text comments/notes.

    Returns:
        The newly created Account instance.
    """
    account = Account(
        user_id=user_id,
        name=name,
        category=category,
        provider=provider,
        account_number_encrypted=account_number_encrypted,
        balance=balance,
        credit_limit=credit_limit,
        interest_rate=interest_rate,
        billing_cycle=billing_cycle,
        next_due_date=next_due_date,
        notes_encrypted=notes_encrypted,
        creator_user_id=creator_user_id,
        editor_user_id=creator_user_id,
        website_url=website_url,
        website_username=website_username,
        website_password=website_password,
        notes=notes,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    logger.info("Created account '%s' (id=%s) for user %s", name, account.id, user_id)
    return account


def get_account(db: Session, account_id: str) -> Account | None:
    """Fetch a single account by ID.

    Args:
        db: An active database session.
        account_id: The account's UUID string.

    Returns:
        The Account or None if not found.
    """
    stmt = select(Account).where(Account.id == account_id)
    return db.execute(stmt).scalar_one_or_none()


def list_accounts(
    db: Session,
    user_id: str,
    category: str | None = None,
    fetch_all: bool = False,
) -> list[Account]:
    """List all accounts for a user (or all users if fetch_all), optionally filtered by category.

    Args:
        db: An active database session.
        user_id: The owning user's ID.
        category: Optional category filter.
        fetch_all: If True, list accounts of all users.

    Returns:
        A list of Account instances.
    """
    stmt = select(Account)
    if not fetch_all:
        stmt = stmt.where(Account.user_id == user_id)
    if category:
        stmt = stmt.where(Account.category == category)
    stmt = stmt.order_by(Account.next_due_date.asc().nullslast(), Account.name)
    return list(db.execute(stmt).scalars().all())


def update_account(db: Session, account_id: str, editor_user_id: str | None = None, **fields: object) -> Account | None:
    """Update fields on an existing account.

    Args:
        db: An active database session.
        account_id: The account's UUID string.
        editor_user_id: The user performing the update.
        **fields: Keyword arguments of column names to new values.

    Returns:
        The updated Account, or None if not found.
    """
    account = get_account(db, account_id)
    if account is None:
        return None
    for key, value in fields.items():
        if hasattr(account, key):
            setattr(account, key, value)
    if editor_user_id:
        account.editor_user_id = editor_user_id
    account.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(account)
    logger.info("Updated account %s", account_id)
    return account


def delete_account(db: Session, account_id: str) -> bool:
    """Delete an account and all related payments/attachments (CASCADE).

    Args:
        db: An active database session.
        account_id: The account's UUID string.

    Returns:
        True if deleted, False if not found.
    """
    account = get_account(db, account_id)
    if account is None:
        return False
    db.delete(account)
    db.commit()
    logger.info("Deleted account %s", account_id)
    return True
