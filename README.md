# FamiCent — Family Financial Account Management

FamiCent is a locally-hosted web application for managing family financial accounts and obligations. It helps households track utility bills, credit card balances, recurring payments, insurance premiums, and subscriptions in one secure, centralized place. 

The application is built on a lightweight Flask backend and served locally on `localhost`.

---

## Key Features

- **Unified Dashboard**: Displays total outstanding balances, payments made in the current month, accounts due within the next 30 days, and a grouped list of accounts with recent payments.
- **Bank-Grade Security**:
  - All sensitive fields (e.g., account numbers, notes, payment reference numbers) are encrypted at rest using **AES-256-GCM**.
  - Passwords are securely hashed using **Argon2id**.
  - Mandatory **TOTP-based MFA** (using standard authenticator apps) for all accounts, with no bypass route.
- **Account Management**: Full CRUD operations for utilities, credit cards, loans, insurance, subscriptions, and custom categories.
- **Payment Tracking**: Record and edit payments, track history, and monitor upcoming obligations.
- **Admin Database Viewer (Looker)**: Allows administrators to run read-only SQLite queries to inspect the system tables.
- **Profile & Session Settings**: Configure custom session timeouts (60s to 24h) and reset MFA configurations.
- **Theme Toggle**: Real-time persisted theme switcher supporting both dark and light UI states without flashes on load.
- **Sidebar Auto-Hide**: Hides the sidebar automatically after 3 minutes of inactivity to expand workspace visibility, reverting instantly on cursor activity.
- **Interactive Local Documentation**: Access a comprehensive operational guide via the `/docs` route directly.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Language** | Python 3.11+ |
| **Backend** | Flask |
| **Frontend** | Vanilla HTML5 / CSS3 / JavaScript (ES6+) |
| **Database & ORM** | SQLite3 + SQLAlchemy 2.x + Alembic |
| **Security & Crypto** | `cryptography` (AES-256-GCM), `argon2-cffi` (Argon2id), `pyotp` (TOTP) |
| **Testing** | `pytest` |

---

## Getting Started

### Prerequisites
- Python 3.11 or higher installed on your system.

### Setup and Installation

1. **Clone and navigate to the project directory**:
   ```powershell
   cd d:\projects\FamiCent_Flask_agy
   ```

2. **Create and activate a virtual environment**:
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

3. **Install development dependencies**:
   ```powershell
   pip install -e ".[dev]"
   ```

4. **Initialize/Upgrade database schema**:
   ```powershell
   alembic upgrade head
   ```

5. **Install automated version hooks**:
   ```powershell
   python .hooks/install_hooks.py
   ```

---

## Running the Application

To run the Flask development server:
```powershell
python -m famicent.app
```
By default, the server runs on `http://127.0.0.1:4010`.

---

## Running Tests

We use `pytest` for unit and integration testing. Run the test suite using:
```powershell
.venv\Scripts\python -m pytest
```

---

## Coding and Versioning Rules

We enforce strict coding conventions (PEP 8, type hints, max line length of 100) and automated versioning.

### Automated Version Bumping
The project features an automated pre-commit hook script located at `.hooks/bump_version.py`. 
- Every git commit automatically increments the **patch** version number (`p += 1`).
- Bumping triggers rolling increments: if `p` reaches 9, it resets to 0 and bumps the minor version (`n`). If `n` reaches 9, it resets to 0 and bumps the major version (`m`).
- Do not bump versions manually in the code.

### Commit Message Format
All commits are automatically prefixed by the hook with version and build timestamp:
```
v{m.n.p} build {yyyy-mm-dd-hhmm} {scope}: {description}
```
Example:
```
v1.0.1 build 2026-07-10-1430 feat(auth): add admin password notifier
```
