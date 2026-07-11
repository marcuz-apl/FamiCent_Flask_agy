# FamiCent — Product Requirements Document

## 1. Overview

**FamiCent** is a locally-hosted web application for managing family financial accounts and obligations. It helps households track utility bills, credit-card balances, recurring payments, insurance premiums, and other financial commitments in one secure, centralized place. The app runs on `localhost` via a lightweight Flask server and is accessed through the browser.

---

## 2. Goals

| # | Goal |
|---|------|
| G1 | Provide a single dashboard showing all family financial accounts, upcoming due dates, and payment status. |
| G2 | Ensure **bank-grade security** for highly sensitive financial data. |
| G3 | Store all data locally in an **SQLite3** database — no cloud dependency. |
| G4 | Deliver an intuitive web UI suitable for non-technical family members. |
| G5 | Support multiple account types with flexible scheduling (one-time, monthly, yearly, custom). |
| G6 | Enforce **semantic versioning** (`m.n.p`) with automated version bumps via pre-commit hooks. |

---

## 3. Toolset Selection

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Language** | Python 3.11+ | Rich ecosystem, rapid prototyping, strong crypto libs |
| **Backend** | Flask | Lightweight, minimal boilerplate, built-in dev server |
| **Frontend** | Vanilla HTML / CSS / JavaScript | No framework overhead; full CSS3 for premium styling |
| **Templating** | Jinja2 (via Flask) | Server-rendered pages with dynamic content |
| **Database** | SQLite3 (via `sqlite3` stdlib or `SQLAlchemy`) | Lightweight, zero-config, single-file storage |
| **ORM / Migrations** | SQLAlchemy 2.x + Alembic | Type-safe queries, schema versioning |
| **Encryption** | `cryptography` (AES-256-GCM) | Encrypts sensitive fields at rest |
| **Auth / MFA** | `pyotp` (TOTP) + Argon2 (`argon2-cffi`) | Password hashing + Time-based one-time passwords |
| **Versioning** | Manual `__version__` + pre-commit hook | Semantic versioning with pre-commit automation |
| **Testing** | pytest | Unit + integration tests |
| **Logging** | Python `logging` module | Structured log files (no sensitive data) |

---

## 4. Functional Requirements

### 4.1 Authentication & Security

- **FR-SEC-01** Every session requires a master password before any financial data is accessible.
- **FR-SEC-02** Master password is hashed with Argon2id (cost factor tuned for performance).
- **FR-SEC-03** MFA (TOTP via authenticator app) is **mandatory** — no bypass option.
- **FR-SEC-04** Sensitive database fields are encrypted at rest using AES-256-GCM; the decryption key is derived from the master password and never stored.
- **FR-SEC-05** Auto-lock after 5 minutes of inactivity (server-side session timeout).
- **FR-SEC-06** No sensitive data cached in browser storage (localStorage, sessionStorage, cookies carry only session tokens).

### 4.2 User Management

- **FR-USR-MGT-01** An **admin** user is created on first initialization with a hardcoded initial password `admin123`.
- **FR-USR-MGT-02** Upon first login as admin, a notification banner must appear prompting the admin to change the password.
- **FR-USR-MGT-03** Password change is **not mandatory** for the admin, but if the admin chooses to generate a new password, the system must produce a cryptographically random one (24+ chars, mixed case, digits, symbols).
- **FR-USR-MGT-04** After the admin changes their password (manually or via generation), the notification banner disappears permanently.
- **FR-USR-MGT-05** Support multiple family profiles under one master password.
- **FR-USR-MGT-06** Per-profile view permissions (read-only vs. full access).

### 4.3 Account Management

- **FR-ACC-01** Create, read, update, delete (CRUD) accounts for categories:
  - Utility Bills (electric, water, gas, internet)
  - Credit Cards
  - Loans / Mortgages
  - Insurance (home, auto, life, health)
  - Subscriptions (streaming, software)
  - Custom categories
- **FR-ACC-02** Each account stores: name, category, provider, account number (encrypted), balance / limit, interest rate, billing cycle, next due date, notes.
- **FR-ACC-03** Attach uploaded documents (PDFs, images) — stored encrypted on disk.

### 4.4 Payment Tracking

- **FR-PAY-01** Record payments with date, amount, method, and reference number.
- **FR-PAY-02** Automatic reminders for upcoming due dates (configurable: 7 / 3 / 1 day before).
- **FR-PAY-03** Payment history view with filtering and sorting.
- **FR-PAY-04** Recurring-payment automation hints (flag bills that repeat monthly/yearly).

### 4.5 Dashboard & Reporting

- **FR-DASH-01** Home screen showing: total outstanding, upcoming payments (next 30 days), accounts sorted by category.
- **FR-DASH-02** Monthly spending summary with pie/bar charts (via Chart.js or vanilla SVG).
- **FR-DASH-03** Export to CSV / PDF for personal records.

### 4.6 Versioning

- **FR-VER-01** Application version follows **Semantic Versioning** in the format `m.n.p` where:
  - `m` (major) is unbounded integer, starts at `1`.
  - `n` (minor) is a single digit `0-9`.
  - `p` (patch) is a single digit `0-9`.
- **FR-VER-02** Version is stored in `src/famicent/__init__.py` as `__version__ = "1.0.0"`.
- **FR-VER-03** A pre-commit hook automatically bumps the patch version (`p += 1`) on every commit.
- **FR-VER-04** When `p` reaches `9`, it resets to `0` and `n` increments by `1`.
- **FR-VER-05** When `n` reaches `9`, it resets to `0` and `m` increments by `1`.
- **FR-VER-06** Commit messages follow the format: `v{m.n.p} build {yyyy-mm-dd-hhmm} {feat scope}: {description}`.

---

## 5. Non-Functional Requirements

| ID | Requirement |
|----|------------|
| NFR-01 | **Performance**: Dashboard loads in < 2 seconds on a typical laptop. |
| NFR-02 | **Local-only**: Runs on `localhost`; no external network calls required. |
| NFR-03 | **Offline-first**: Fully functional without internet connectivity. |
| NFR-04 | **Backup**: Built-in export/backup to encrypted archive. |
| NFR-05 | **Accessibility**: High-contrast theme, scalable fonts, responsive layout. |
| NFR-06 | **Version traceability**: Every git commit carries an auto-generated version tag in its message. |
| NFR-07 | **Browser support**: Modern evergreen browsers (Chrome, Firefox, Edge). |

---

## 6. Data Model (High-Level)

```
User
├── id (UUID)
├── username (unique)
├── role (admin / member)
├── password_hash (BLOB, Argon2id)
├── mfa_secret_encrypted (BLOB)
├── mfa_enabled (BOOLEAN)
├── password_changed (BOOLEAN)
├── profile_name
├── created_at
│
Account
├── id (UUID)
├── user_id (FK)
├── name
├── category (enum)
├── provider
├── account_number_encrypted (BLOB)
├── balance / limit
├── interest_rate
├── billing_cycle (enum)
├── next_due_date
├── notes_encrypted (BLOB)
│
Payment
├── id (UUID)
├── account_id (FK)
├── amount
├── payment_date
├── method (cash, card, transfer)
├── reference_number_encrypted (BLOB)
│
Attachment
├── id (UUID)
├── account_id (FK)
├── file_path_encrypted (BLOB)
├── mime_type
├── uploaded_at
```

---

## 7. Project Structure (Proposed)

```
FamiCent/
├── PRD.md                  ← this file
├── AGENTS.md               ← agent instructions
├── rules.md                ← coding standards
├── pyproject.toml          ← Python project config
├── alembic.ini             ← migration config
├── README.md
├── src/
│   └── famicent/
│       ├── __init__.py     ← __version__ lives here
│       ├── app.py          ← Flask application factory
│       ├── auth/           ← password, MFA, session
│       │   ├── __init__.py
│       │   ├── routes.py   ← login/logout/mfa endpoints
│       │   ├── manager.py  ← password hashing, session logic
│       │   └── mfa.py      ← TOTP helpers
│       ├── db/             ← database layer
│       │   ├── __init__.py
│       │   ├── engine.py   ← SQLAlchemy engine + session
│       │   ├── models.py   ← all ORM models
│       │   └── crypto.py   ← AES-256-GCM encrypt/decrypt
│       ├── views/          ← Flask route blueprints
│       │   ├── __init__.py
│       │   ├── dashboard.py
│       │   ├── accounts.py
│       │   ├── payments.py
│       │   └── settings.py
│       ├── services/       ← business logic
│       │   ├── __init__.py
│       │   ├── account_svc.py
│       │   └── payment_svc.py
│       ├── utils/
│       │   ├── __init__.py
│       │   └── helpers.py
│       ├── static/         ← CSS, JS, images
│       │   ├── css/
│       │   │   └── style.css
│       │   ├── js/
│       │   │   └── app.js
│       │   └── img/
│       └── templates/      ← Jinja2 HTML templates
│           ├── base.html
│           ├── login.html
│           ├── mfa.html
│           ├── dashboard.html
│           ├── accounts.html
│           ├── payments.html
│           └── settings.html
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_db.py
│   └── test_services/
├── migrations/
│   ├── env.py
│   └── versions/
├── .hooks/
│   └── bump_version.py    ← pre-commit version bump script
└── assets/
    └── icons/
```

---

## 8. Milestones

| Phase | Description | Target |
|-------|-------------|--------|
| M0 | Repo scaffolding, toolchain setup, versioning infra | Week 1-2 |
| M1 | Auth module (password + Argon2 + MFA) | Week 3-4 |
| M2 | Database schema + SQLAlchemy models | Week 3-4 |
| M3 | Login page + admin onboarding + password-change notifier | Week 5 |
| M4 | Dashboard + account CRUD | Week 6-8 |
| M5 | Payment tracking + reminders | Week 9-10 |
| M6 | Charts, reporting, export | Week 11-12 |
| M7 | Encryption at rest, backup | Week 13 |
| M8 | Testing, polish, packaging | Week 14-15 |
| M9 | Beta release | Week 16 |

---

## 9. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Losing master password = data loss | Critical | Provide secure recovery seed phrase option; encourage backups |
| SQLite corruption | High | WAL mode + periodic integrity checks + encrypted backups |
| MFA enrollment friction | Medium | Clear onboarding flow with QR-code scanning |
| Performance with large datasets | Low | Indexed queries; pagination on views |
| Hardcoded initial password exposure | High | `admin123` is only used in first-run init; must be changed or regenerated on first login |
| Pre-commit hook slows workflow | Low | Hook runs fast (file read/write only); configurable via `--no-verify` if needed |
| Browser security (XSS, CSRF) | High | Flask-WTF CSRF tokens; strict Content-Security-Policy headers; input sanitization |

---

## 10. Success Metrics

- Zero data-loss incidents in first 6 months.
- Dashboard load < 2 s on mid-range hardware.
- 100 % of sensitive fields encrypted at rest.
- All critical paths covered by automated tests (target > 80 % coverage).
- Every git commit carries a valid versioned commit message.
- Admin password-change notifier appears reliably on first admin login.
