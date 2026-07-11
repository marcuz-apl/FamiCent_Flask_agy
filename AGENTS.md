# FamiCent — Agent Instructions (AGENTS.md)

> Instructions for AI coding agents working on the FamiCent codebase.

---

## 1. Project Purpose

FamiCent is a **family financial-account management web app** that runs locally on `localhost`. It tracks utility bills, credit cards, loans, insurance, subscriptions, and custom accounts. All data is stored **locally** in an encrypted SQLite3 database. Access requires a **master password + TOTP-based MFA**. The frontend is served by a lightweight Flask backend and rendered in the browser.

---

## 2. Tech Stack

| Category | Choice |
|----------|--------|
| Language | Python 3.11+ |
| Backend | Flask |
| Frontend | Vanilla HTML / CSS / JavaScript |
| Templating | Jinja2 (via Flask) |
| DB | SQLite3 + SQLAlchemy 2.x + Alembic |
| Crypto | `cryptography` (AES-256-GCM), Argon2id (`argon2-cffi`) |
| MFA | TOTP via `pyotp` |
| Versioning | Manual `__version__` + pre-commit hook |
| Tests | pytest |
| Packaging | Single `pip install` or Docker (optional) |

---

## 3. Code Organization

```
src/famicent/
├── __init__.py        ← __version__ lives here
├── app.py             ← Flask application factory
├── auth/              ← login, password hash, MFA, session
│   ├── routes.py      ← login/logout/mfa endpoints
│   ├── manager.py     ← password hashing, session logic
│   └── mfa.py         ← TOTP helpers
├── db/                ← SQLAlchemy engine, models, crypto layer
│   ├── engine.py
│   ├── models.py
│   └── crypto.py
├── views/             ← Flask route blueprints
│   ├── dashboard.py
│   ├── accounts.py
│   ├── payments.py
│   └── settings.py
├── services/          ← business logic (accounts, payments)
│   ├── account_svc.py
│   └── payment_svc.py
├── utils/             ← shared helpers
├── static/            ← CSS, JS, images
│   ├── css/style.css
│   ├── js/app.js
│   └── img/
└── templates/         ← Jinja2 HTML templates
    ├── base.html
    ├── login.html
    ├── dashboard.html
    └── ...
tests/                 ← pytest suite
migrations/            ← Alembic migrations
.hooks/                ← pre-commit scripts
```

- **No circular imports.** Layer order: `utils → db → services → views → auth`.
- **Services** must not import view/route code. **Views** must not import directly into `db` — use services.
- **Models** live in `src/famicent/db/models.py`.

---

## 4. Development Workflow

### 4.1 Setup

```powershell
cd D:\projects\FamiCent-agy
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
alembic upgrade head
```

### 4.2 Running

```powershell
python -m famicent.app
```

The app starts on `http://localhost:5000` by default.

### 4.3 Testing

```powershell
pytest -v
```

### 4.4 Migrations

```powershell
alembic revision --autogenerate -m "description"
alembic upgrade head
```

---

## 5. Security Rules (NON-NEGOTIABLE)

1. **Never log** passwords, tokens, or decrypted data.
2. **Never commit** `.env`, `*.key`, or database files. They are in `.gitignore`.
3. All sensitive fields in models must use `LargeBinary` (encrypted BLOB).
4. Key derivation uses `scrypt` or `Argon2id` with a per-installation salt.
5. MFA is **always required** — there is no "skip MFA" path.
6. Session timeout: **5 minutes** of inactivity triggers auto-lock (server-side session expiry).
7. No sensitive data in browser storage (localStorage, sessionStorage). Session tokens only in secure, HttpOnly cookies.
8. All forms must include **CSRF tokens** (Flask-WTF or manual implementation).
9. Set strict **Content-Security-Policy** headers to prevent XSS.

---

## 6. Versioning Rules

### 6.1 Version Format

- Version is `m.n.p` stored in `src/famicent/__init__.py` as `__version__ = "1.0.0"`.
- `m` (major) — unbounded integer, starts at 1.
- `n` (minor) — single digit 0-9.
- `p` (patch) — single digit 0-9.

### 6.2 Increment Logic

| Condition | Action |
|-----------|--------|
| Normal commit | `p += 1` |
| `p == 9` | Reset `p = 0`, increment `n += 1` |
| `n == 9` | Reset `n = 0`, increment `m += 1` |

### 6.3 Pre-Commit Hook

- Located at `.hooks/bump_version.py`.
- Runs on every `git commit`.
- Reads current version from `src/famicent/__init__.py`, bumps it, writes it back.
- Appends the version timestamp to the commit message.

### 6.4 Commit Message Format

```
v{m.n.p} build {yyyy-mm-dd-hhmm} {feat scope}: {description}
```

Examples:
```
v1.0.1 build 2026-07-08-1430 feat(auth): add admin password notifier
v1.0.2 build 2026-07-08-1500 fix(views): dashboard layout overflow
v1.1.0 build 2026-07-09-0900 feat(acc): add loan category support
```

---

## 7. Admin Onboarding Flow

1. On first run, the app creates an `admin` user with password `admin123` (hashed with Argon2id).
2. On first login, the web UI shows a **yellow warning banner** at the top of the dashboard: "Admin password is set to default. Please change it or generate a secure password."
3. The banner offers two buttons:
   - **Change Password** — opens a modal to enter a new password manually.
   - **Generate Password** — creates a 24-char cryptographically random password, displays it to the user, and marks it as changed.
4. Once the password is changed (manually or generated), the banner is dismissed permanently and `password_changed = true` is stored in the DB.
5. The banner **does not reappear** even after logout/login cycles.

---

## 8. Coding Conventions

- Follow **PEP 8** with a maximum line length of **100 characters**.
- Use **type hints** everywhere.
- Docstrings: Google style for public APIs.
- Private methods/functions prefixed with `_`.
- Constants in `UPPER_SNAKE_CASE` in a `constants.py` or module-level.
- Use `pathlib.Path` instead of `os.path`.
- All Python files start with `from __future__ import annotations`.
- Frontend JS uses vanilla ES6+ — no frameworks, no transpilers.
- CSS uses custom properties (variables) for theming.

---

## 9. Testing Expectations

- Every new service function needs at least one unit test.
- Route/view changes need at least one integration test (using Flask test client).
- Test database uses an in-memory SQLite (`:memory:`) — never touch the real DB file.
- Use `conftest.py` fixtures for Flask test client and authenticated session mocks.

---

## 10. Agent-Specific Notes

- **Always read `rules.md`** before making changes — it contains stricter constraints.
- When adding a new model, **also create an Alembic migration**.
- When adding a new page/route, register the blueprint in `app.py` and add it to the navigation.
- When in doubt, **ask** — security-sensitive decisions should be confirmed.
- Do **not** modify `.gitignore`, CI config, or root-level tooling without explicit permission.
- The pre-commit hook at `.hooks/bump_version.py` is the **only** place that modifies version numbers — never bump version manually in code.
