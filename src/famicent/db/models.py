"""SQLAlchemy ORM models for FamiCent.

Defines User, Account, Payment, and Attachment tables following the data model
in the PRD. All sensitive columns use LargeBinary (R14). Every table includes
created_at and updated_at timestamps (R13).
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    event,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class UserRole(str, enum.Enum):
    """User permission roles."""
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class AccountCategory(str, enum.Enum):
    """Supported account categories (FR-ACC-01)."""
    UTILITY = "utility"
    CREDIT_CARD = "credit_card"
    LOAN = "loan"
    INSURANCE = "insurance"
    SUBSCRIPTION = "subscription"
    CUSTOM = "custom"


class BillingCycle(str, enum.Enum):
    """Payment frequency options."""
    ONE_TIME = "one_time"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class PaymentMethod(str, enum.Enum):
    """How a payment was made."""
    CASH = "cash"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    CHECK = "check"
    PAD = "pad"
    OTHER = "other"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class User(Base):
    """Application user (admin or family member)."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    role: Mapped[str] = mapped_column(
        Enum(UserRole), nullable=False, default=UserRole.VIEWER
    )
    password_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    mfa_secret_encrypted: Mapped[bytes | None] = mapped_column(
        LargeBinary, nullable=True
    )
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mfa_enforced: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    password_changed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    profile_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    session_timeout: Mapped[int] = mapped_column(
        Integer, default=300, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    accounts: Mapped[list[Account]] = relationship(
        "Account", back_populates="user", cascade="all, delete-orphan",
        foreign_keys="Account.user_id"
    )


class Account(Base):
    """A financial account tracked by the family."""

    __tablename__ = "accounts"
    __table_args__ = (
        Index("ix_accounts_category", "category"),
        Index("ix_accounts_next_due_date", "next_due_date"),
        Index("ix_accounts_user_id", "user_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(
        Enum(AccountCategory), nullable=False, default=AccountCategory.CUSTOM
    )
    provider: Mapped[str | None] = mapped_column(String(200), nullable=True)
    account_number_encrypted: Mapped[bytes | None] = mapped_column(
        LargeBinary, nullable=True
    )
    balance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    credit_limit: Mapped[float | None] = mapped_column(Float, nullable=True)
    interest_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    billing_cycle: Mapped[str] = mapped_column(
        Enum(BillingCycle), nullable=False, default=BillingCycle.MONTHLY
    )
    next_due_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    creator_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    editor_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    website_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    website_username: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )
    website_password: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(
        String(2000), nullable=True
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="accounts", foreign_keys="Account.user_id")
    payments: Mapped[list[Payment]] = relationship(
        "Payment", back_populates="account", cascade="all, delete-orphan"
    )
    attachments: Mapped[list[Attachment]] = relationship(
        "Attachment", back_populates="account", cascade="all, delete-orphan"
    )


class Payment(Base):
    """A single payment against an account."""

    __tablename__ = "payments"
    __table_args__ = (
        Index("ix_payments_account_id", "account_id"),
        Index("ix_payments_payment_date", "payment_date"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    payment_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    method: Mapped[str] = mapped_column(
        Enum(PaymentMethod), nullable=False, default=PaymentMethod.BANK_TRANSFER
    )
    reference_number_encrypted: Mapped[bytes | None] = mapped_column(
        LargeBinary, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    creator_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    editor_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    account: Mapped[Account] = relationship("Account", back_populates="payments")


class Attachment(Base):
    """An encrypted file attachment linked to an account."""

    __tablename__ = "attachments"
    __table_args__ = (Index("ix_attachments_account_id", "account_id"),)

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    file_path_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    account: Mapped[Account] = relationship("Account", back_populates="attachments")
