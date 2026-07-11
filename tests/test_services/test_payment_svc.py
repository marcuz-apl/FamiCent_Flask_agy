"""Unit tests for payment_svc.py."""
from __future__ import annotations

import pytest
from datetime import datetime, timedelta

from famicent.db.models import AccountCategory, PaymentMethod
from famicent.services.account_svc import create_account
from famicent.services.payment_svc import (
    delete_payment,
    get_monthly_spending,
    get_payment,
    get_total_outstanding,
    get_upcoming_payments,
    list_payments,
    record_payment,
)


@pytest.fixture
def account(db_session, admin_user):
    """Helper: create a test account."""
    return create_account(
        db_session,
        user_id=admin_user.id,
        name="Test Account",
        category=AccountCategory.UTILITY.value,
        balance=200.0,
        next_due_date=datetime.utcnow() + timedelta(days=5),
    )


class TestRecordPayment:
    def test_record_basic_payment(self, db_session, account):
        payment = record_payment(
            db_session,
            account_id=account.id,
            amount=150.0,
            payment_date=datetime.utcnow(),
        )
        assert payment.id is not None
        assert payment.amount == 150.0

    def test_record_with_method(self, db_session, account):
        payment = record_payment(
            db_session,
            account_id=account.id,
            amount=75.0,
            payment_date=datetime.utcnow(),
            method=PaymentMethod.CREDIT_CARD.value,
        )
        assert payment.method == PaymentMethod.CREDIT_CARD.value


class TestGetPayment:
    def test_get_existing(self, db_session, account):
        p = record_payment(db_session, account_id=account.id,
                            amount=50.0, payment_date=datetime.utcnow())
        fetched = get_payment(db_session, p.id)
        assert fetched is not None
        assert fetched.id == p.id

    def test_get_nonexistent_returns_none(self, db_session):
        assert get_payment(db_session, "bad-id") is None


class TestListPayments:
    def test_list_by_account(self, db_session, account):
        record_payment(db_session, account_id=account.id,
                       amount=10.0, payment_date=datetime.utcnow())
        record_payment(db_session, account_id=account.id,
                       amount=20.0, payment_date=datetime.utcnow())
        payments = list_payments(db_session, account_id=account.id)
        assert len(payments) == 2

    def test_list_by_user(self, db_session, account, admin_user):
        record_payment(db_session, account_id=account.id,
                       amount=99.0, payment_date=datetime.utcnow())
        payments = list_payments(db_session, user_id=admin_user.id)
        assert len(payments) == 1


class TestDeletePayment:
    def test_delete_existing(self, db_session, account):
        p = record_payment(db_session, account_id=account.id,
                            amount=30.0, payment_date=datetime.utcnow())
        assert delete_payment(db_session, p.id) is True
        assert get_payment(db_session, p.id) is None

    def test_delete_nonexistent_returns_false(self, db_session):
        assert delete_payment(db_session, "nope") is False


class TestAggregates:
    def test_total_outstanding(self, db_session, admin_user, account):
        total = get_total_outstanding(db_session, admin_user.id)
        assert total == 200.0

    def test_monthly_spending(self, db_session, admin_user, account):
        now = datetime.utcnow()
        record_payment(db_session, account_id=account.id,
                       amount=100.0, payment_date=now)
        record_payment(db_session, account_id=account.id,
                       amount=50.0, payment_date=now)
        total = get_monthly_spending(db_session, admin_user.id, now.year, now.month)
        assert total == 150.0

    def test_upcoming_payments(self, db_session, admin_user, account):
        upcoming = get_upcoming_payments(db_session, admin_user.id, days=30)
        assert len(upcoming) == 1
        assert upcoming[0].id == account.id
