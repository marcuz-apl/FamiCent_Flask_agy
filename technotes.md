# FamiCent — Technical Documentation & Architecture Notes

This document provides deep technical details on the design, architecture, security model, and implementation guidelines of FamiCent.

---

## 1. Architectural Design & Boundaries

FamiCent follows a strict layered architecture to maintain clear boundaries and prevent circular dependencies:

```
┌───────────────────────────────────────────────┐
│                    auth                       │
│    (Session Manager, MFA helpers, Decorators) │
└───────────────────────┬───────────────────────┘
                        ▼
┌───────────────────────────────────────────────┐
│                    views                      │
│      (Flask blueprints, Route controllers)    │
└───────────────────────┬───────────────────────┘
                        ▼
┌───────────────────────────────────────────────┐
│                   services                    │
│    (Business logic for accounts & payments)   │
└───────────────────────┬───────────────────────┘
                        ▼
┌───────────────────────────────────────────────┐
│                      db                       │
│     (SQLAlchemy models, Crypto engine, WAL)   │
└───────────────────────┬───────────────────────┘
                        ▼
┌───────────────────────────────────────────────┐
│                     utils                     │
│               (Helpers, Constants)            │
└───────────────────────────────────────────────┘
```

- **Imports direction**: Code must only import down the stack (`auth → views → services → db → utils`).
- **No Direct DB Access in Views**: View blueprints must use service functions (e.g., [account_svc.py](file:///d:/projects/FamiCent_Flask_agy/src/famicent/services/account_svc.py)) instead of querying SQLAlchemy models directly.

---

## 2. Security Architecture

### 2.1 Password Hashing (Argon2id)
Passwords are encrypted using Argon2id via the `argon2-cffi` library. Parameters (R18) are hardcoded in the session manager to resist GPU/ASIC-based cracking:
- **Time Cost (`time_cost`)**: `3`
- **Memory Cost (`memory_cost`)**: `65536` (64 MB)
- **Parallelism (`parallelism`)**: `4`

### 2.2 Field-Level Encryption (AES-256-GCM)
Sensitive database columns (e.g., `account_number_encrypted`, `notes_encrypted`, `reference_number_encrypted`) are stored as binary payloads (`LargeBinary`).
- **Algorithm**: AES-256-GCM (96-bit random nonce generated per encryption).
- **Key Derivation (scrypt)**: Keys are derived dynamically using `scrypt` from the master password (R20) with parameters:
  - `n` = `16384`
  - `r` = `8`
  - `p` = `1`
  - Unique 16-byte random salt generated per execution.
  - The derived key is never persisted to the disk or session storage.

### 2.3 Multi-Factor Authentication (TOTP)
MFA is mandatory. Standard authenticator apps register FamiCent using the provisioning URI:
- **Algorithm**: TOTP (RFC 6238)
- **Token Length**: 6 digits
- **Time Step**: 30 seconds
- **Hash function**: SHA-256 (instead of default SHA-1)

### 2.4 Session Security & Hardening
- **Inactivity Timeout**: Server-side session inactivity check is performed on every request (defaulting to 300 seconds / 5 minutes). When the timeout is hit, session data is cleared, requiring a re-login.
- **Cookies**: Session cookies are configured with `HttpOnly=True` and `SameSite=Strict`.
- **Security Headers**:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Content-Security-Policy`: Restricts scripts, styles, and images to self-origin (`'self'`), only permitting specific Google Fonts CDNs.

---

## 3. Database Engine & Alembic Migrations

- **SQLite WAL Mode**: To support safe concurrent reading and writing, SQLite is initialized in Write-Ahead Logging (WAL) mode on connection:
  ```sql
  PRAGMA journal_mode=WAL;
  PRAGMA foreign_keys=ON;
  ```
- **Index Optimization**: Indexes are defined on frequently queried fields like `user_id`, `category`, and `next_due_date` in the `accounts` table, and `payment_date` in the `payments` table.
- **Schema Migrations**: Schema alterations must be tracked using Alembic migrations inside the `migrations/versions/` directory. Direct database table structure modification is strictly prohibited.

---

## 4. User Permission & Role Matrix

FamiCent supports three permission levels:

| Action / Capability | Viewer (`viewer`) | Editor (`editor`) | Admin (`admin`) |
|---|---|---|---|
| View Dashboard & Accounts | Yes (Own data only) | Yes (Own data only) | Yes (All data) |
| Read-Only SQL Query (Looker) | No | No | Yes |
| CRUD Accounts & Payments | No | Yes (Own only) | Yes (All) |
| Manage Users / Reset MFA | No | No | Yes |
| Configure Timeout Settings | Yes (Own account) | Yes (Own account) | Yes (Own + Others) |

*Note: There is a maximum limit of **5 non-admin** family member profiles.*

---

## 5. Admin Onboarding Banner Implementation

To mitigate the risk of default admin credentials:
1. First application initialization creates the superadmin user: `admin` / `admin123`.
2. Upon login, if `password_changed` is false, a banner is rendered at the top of the dashboard.
3. The banner provides modal prompts for manual password updating or automated secure password generation (24-character mixed-set sequence).
4. Once changed, `password_changed` is set to `True` in the database, dismissing the banner permanently.
