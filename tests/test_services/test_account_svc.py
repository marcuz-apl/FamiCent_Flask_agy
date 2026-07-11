"""Unit tests for account_svc.py."""
from __future__ import annotations

import pytest
from datetime import datetime, timedelta

from famicent.db.models import AccountCategory, BillingCycle
from famicent.services.account_svc import (
    create_account,
    delete_account,
    get_account,
    list_accounts,
    update_account,
)


class TestCreateAccount:
    def test_create_minimal(self, db_session, admin_user):
        account = create_account(
            db_session,
            user_id=admin_user.id,
            name="Electric Bill",
            category=AccountCategory.UTILITY.value,
        )
        assert account.id is not None
        assert account.name == "Electric Bill"
        assert account.balance == 0.0

    def test_create_with_all_fields(self, db_session, admin_user):
        due = datetime.utcnow() + timedelta(days=10)
        account = create_account(
            db_session,
            user_id=admin_user.id,
            name="Visa Card",
            category=AccountCategory.CREDIT_CARD.value,
            provider="Chase",
            balance=1500.0,
            credit_limit=5000.0,
            interest_rate=19.99,
            billing_cycle=BillingCycle.MONTHLY.value,
            next_due_date=due,
        )
        assert account.provider == "Chase"
        assert account.credit_limit == 5000.0
        assert account.interest_rate == 19.99


class TestGetAccount:
    def test_get_existing_account(self, db_session, admin_user):
        created = create_account(db_session, user_id=admin_user.id,
                                  name="Loan", category=AccountCategory.LOAN.value)
        fetched = get_account(db_session, created.id)
        assert fetched is not None
        assert fetched.id == created.id

    def test_get_nonexistent_returns_none(self, db_session):
        result = get_account(db_session, "nonexistent-id")
        assert result is None


class TestListAccounts:
    def test_list_all_for_user(self, db_session, admin_user):
        create_account(db_session, user_id=admin_user.id, name="A",
                       category=AccountCategory.UTILITY.value)
        create_account(db_session, user_id=admin_user.id, name="B",
                       category=AccountCategory.LOAN.value)
        accounts = list_accounts(db_session, admin_user.id)
        assert len(accounts) == 2

    def test_list_with_category_filter(self, db_session, admin_user):
        create_account(db_session, user_id=admin_user.id, name="A",
                       category=AccountCategory.UTILITY.value)
        create_account(db_session, user_id=admin_user.id, name="B",
                       category=AccountCategory.LOAN.value)
        utilities = list_accounts(db_session, admin_user.id,
                                   category=AccountCategory.UTILITY.value)
        assert len(utilities) == 1
        assert utilities[0].name == "A"

    def test_list_returns_empty_for_other_user(self, db_session, admin_user, member_user):
        create_account(db_session, user_id=admin_user.id, name="Admin Account",
                       category=AccountCategory.CUSTOM.value)
        member_accounts = list_accounts(db_session, member_user.id)
        assert member_accounts == []


class TestUpdateAccount:
    def test_update_name(self, db_session, admin_user):
        account = create_account(db_session, user_id=admin_user.id,
                                  name="Old Name", category=AccountCategory.CUSTOM.value)
        updated = update_account(db_session, account.id, name="New Name")
        assert updated is not None
        assert updated.name == "New Name"

    def test_update_nonexistent_returns_none(self, db_session):
        result = update_account(db_session, "bad-id", name="X")
        assert result is None


class TestDeleteAccount:
    def test_delete_existing(self, db_session, admin_user):
        account = create_account(db_session, user_id=admin_user.id,
                                  name="To Delete", category=AccountCategory.CUSTOM.value)
        result = delete_account(db_session, account.id)
        assert result is True
        assert get_account(db_session, account.id) is None

    def test_delete_nonexistent_returns_false(self, db_session):
        result = delete_account(db_session, "does-not-exist")
        assert result is False
