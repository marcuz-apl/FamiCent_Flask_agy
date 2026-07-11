# FamiCent — Coding Rules (rules.md)

> Strict coding standards and constraints for all contributors and AI agents.

---

## 1. General Principles

| Rule | Detail |
|------|--------|
| **R1** | Every Python file must be valid Python 3.11+ with `from __future__ import annotations` at the top. |
| **R2** | Maximum line length: **100** characters. Enforced by `ruff` or `black`. |
| **R3** | No wildcard imports (`from X import *`). |
| **R4** | No bare `except:` clauses — always catch specific exceptions. |
| **R5** | No `print()` in production code. Use the `logging` module. |
| **R6** | Magic numbers and strings are extracted to named constants. |
| **R7** | Functions should be ≤ 50 lines; classes ≤ 300 lines. Refactor when exceeded. |

---

## 2. Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Modules | `lowercase_with_underscores` | `account_service.py` |
| Packages | `lowercase_no_underscores` | `famicent` |
| Classes | `PascalCase` | `AccountService` |
| Functions / methods | `snake_case` | `calculate_interest()` |
| Variables | `snake_case` | `account_balance` |
| Constants | `UPPER_SNAKE_CASE` | `SESSION_TIMEOUT_SECONDS` |
| Private attributes | `_leading_underscore` | `_session_token` |
| Public constants / enums | `UPPER_SNAKE_CASE` | `AccountCategory.UTILITY` |
| CSS classes | `kebab-case` | `.card-header`, `.btn-primary` |
| JS functions | `camelCase` | `fetchAccounts()` |
| HTML IDs | `kebab-case` | `#dashboard-summary` |

---

## 3. Type Hints

```python
from __future__ import annotations

from typing import Optional
from uuid import UUID


def get_account(account_id: UUID) -> Optional[Account]:
    """Return an account by ID, or None."""
    ...
```

- **R8** All function signatures must include type hints for parameters and return values.
- **R9** Use `Optional[T]` for nullable returns; never rely on `None` checks without documentation.
- **R10** Prefer `dataclass` or `pydantic.BaseModel` over plain dicts for structured data.

---

## 4. Database Rules

| Rule | Detail |
|------|--------|
| **R11** | All schema changes go through **Alembic migrations** — no manual SQL. |
| **R12** | Foreign keys must be defined with `ON DELETE CASCADE` or `ON DELETE SET NULL` explicitly. |
| **R13** | Every table must have `created_at` and `updated_at` TIMESTAMP columns. |
| **R14** | Sensitive columns (`account_number`, `notes`, `reference_number`) are stored as `LargeBinary` (encrypted). |
| **R15** | Use SQLAlchemy 2.x `select()` syntax — no legacy `Query` API. |
| **R16** | Enable SQLite **WAL mode** for concurrent-read safety. |
| **R17** | Index foreign keys and frequently queried columns (`next_due_date`, `category`). |

---

## 5. Security Rules

| Rule | Detail |
|------|--------|
| **R18** | Password hashing: **Argon2id** with `time_cost=3`, `memory_cost=65536`, `parallelism=4`. |
| **R19** | Field-level encryption: **AES-256-GCM** via the `cryptography` library. |
| **R20** | Keys are derived from the master password using **scrypt** with `n=16384`, `r=8`, `p=1`. |
| **R21** | MFA uses **TOTP** (RFC 6238), SHA-256, 6-digit codes, 30-second window. |
| **R22** | No sensitive data (passwords, tokens, decrypted fields) may appear in logs. |
| **R23** | Session timeout: **300 seconds** of inactivity triggers auto-lock (server-side). |
| **R24** | All user input must be validated and sanitized before database insertion. |
| **R25** | Attachment files are encrypted before writing to disk; decrypted only in memory during read. |
| **R26** | All forms must include CSRF protection tokens. |
| **R27** | Set `Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options` headers on all responses. |
| **R28** | Session cookies must be `HttpOnly`, `SameSite=Strict`, and `Secure` (when not on localhost). |
| **R29** | No sensitive data in browser localStorage or sessionStorage. |

---

## 6. Frontend Rules (HTML / CSS / JS)

| Rule | Detail |
|------|--------|
| **R30** | All pages extend a shared `base.html` Jinja2 template with consistent nav, header, and footer. |
| **R31** | CSS uses **custom properties** (CSS variables) for all colors, spacing, and typography — defined in `:root`. |
| **R32** | No inline styles. All styling in external `.css` files under `static/css/`. |
| **R33** | No inline `<script>` blocks. All JS in external `.js` files under `static/js/`. |
| **R34** | JavaScript uses **ES6+** syntax (arrow functions, `const`/`let`, template literals, `fetch()`). |
| **R35** | No JS frameworks (React, Vue, etc.) — vanilla JS only. |
| **R36** | All interactive elements must have unique, descriptive `id` attributes for testing. |
| **R37** | Responsive design: mobile-first, works down to 360px viewport width. |
| **R38** | Use semantic HTML5 elements (`<main>`, `<nav>`, `<section>`, `<article>`, `<aside>`). |
| **R39** | Accessibility: all images have `alt` text; all form inputs have `<label>` elements; sufficient color contrast (WCAG AA). |

---

## 7. Admin Password Notifier (Web UI)

| Rule | Detail |
|------|--------|
| **R40** | On first login as admin, display a **yellow warning banner** at the top of the dashboard page. |
| **R41** | Banner text: *"Admin password is set to default. Please change it or generate a secure password."* |
| **R42** | Banner must have two action buttons: **Change Password** and **Generate Password**. |
| **R43** | "Generate Password" must produce a 24+ character password using `secrets.choice()` from `string.ascii_letters + string.digits + string.punctuation`. |
| **R44** | Once the password is changed (manual or generated), set `User.password_changed = True` in the DB and remove the banner. |
| **R45** | The banner must **never reappear** after dismissal. |

---

## 8. Testing Rules

| Rule | Detail |
|------|--------|
| **R46** | Test files mirror source structure: `src/famicent/services/account_svc.py` → `tests/test_services/test_account_svc.py`. |
| **R47** | Every public function must have ≥ 1 test. |
| **R48** | Use fixtures in `conftest.py` for shared setup (Flask test client, DB engine, mock user). |
| **R49** | Integration tests use an in-memory SQLite database (`:memory:`). |
| **R50** | Route tests use Flask's built-in test client (`app.test_client()`). |
| **R51** | Minimum coverage target: **80 %** overall, **100 %** for `auth/` and `db/crypto/`. |

---

## 9. Versioning & Commit Rules

### 9.1 Version Format

- Version lives in `src/famicent/__init__.py`: `__version__ = "1.0.0"`.
- Format: `m.n.p` where:
  - `m` (major) — unbounded integer, starts at 1.
  - `n` (minor) — single digit **0–9**.
  - `p` (patch) — single digit **0–9**.

### 9.2 Bump Rules

| Current State | New State |
|---------------|-----------|
| `1.0.8` | `1.0.9` |
| `1.0.9` | `1.1.0` |
| `1.8.9` | `1.9.0` |
| `1.9.9` | `2.0.0` |
| `9.9.9` | `10.0.0` |

### 9.3 Pre-Commit Hook

| Rule | Detail |
|------|--------|
| **R52** | A pre-commit hook at `.hooks/bump_version.py` runs on every `git commit`. |
| **R53** | The hook reads `__version__` from `src/famicent/__init__.py`, applies the bump rules above, and writes the new value back. |
| **R54** | The hook then rewrites the commit message to prepend: `v{m.n.p} build {yyyy-mm-dd-hhmm} `. |
| **R55** | Original commit message (after the prepended prefix) must follow Conventional Commits format. |

### 9.4 Commit Message Format

```
v{m.n.p} build {yyyy-mm-dd-hhmm} {scope}: {description}
```

| Component | Example |
|-----------|---------|
| Version prefix | `v1.0.1` |
| Timestamp | `2026-07-08-1430` |
| Scope | `auth`, `views`, `db`, `acc`, `pay`, `svc`, `test`, `css`, `js` |
| Description | `add admin password notifier` |

Full example:
```
v1.0.1 build 2026-07-08-1430 feat(auth): add admin password notifier
```

### 9.5 Commit Rules

| Rule | Detail |
|------|--------|
| **R56** | Never bump the version manually in code — the pre-commit hook is the **sole authority**. |
| **R57** | Never skip the pre-commit hook for version changes (no `--no-verify` on feature/fix branches). |
| **R58** | Use [Conventional Commits](https://www.conventionalcommits.org/) scopes: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`. |
| **R59** | Branch naming: `feature/<name>`, `fix/<name>`, `refactor/<name>`. |

---

## 10. File Ignore Patterns (.gitignore)

```
# Environment
.venv/
__pycache__/
*.pyc
.env

# Database
*.db
*.sqlite3
*.sqlite3-shm
*.sqlite3-wal

# Secrets
*.key
*.pem
*.p12

# IDE
.idea/
.vscode/
*.swp

# Build
dist/
build/
*.spec

# Pre-commit version backup
*.bak

# Node (if any tooling added later)
node_modules/
```

---

## 11. Linting & Formatting

| Tool | Config |
|------|--------|
| **Ruff** | `ruff check .` — rules: `E`, `F`, `W`, `I`, `UP`, `B`, `SIM` |
| **Black** | `black --check .` — line-length 100 |
| **MyPy** | `mypy src/` — strict mode |
| **Pre-commit** | Runs ruff, black, mypy, and bump_version on every commit |

Install:

```powershell
pip install ruff black mypy pre-commit
pre-commit install
```

---

## 12. Documentation

- Public APIs must have **Google-style docstrings** with `Args:`, `Returns:`, `Raises:` sections.
- Module-level docstrings describe the purpose of the file.
- Complex algorithms must include a comment explaining the **why**, not just the **what**.
- HTML templates must include a comment at the top: `{# Template: <name> — <purpose> #}`.
