# FairDrop — Member 2 Progress Record

Updated UTC: 2026-10-03T16:45:00Z
Member: Member 2 (Security Owner)
Branch: feature/m2-security
Actual Head: Uncommitted feature branch

## Assigned Task
Authentication, durable sessions, authorization, and abuse protection (Phases 0–1, 4 security slices).

## Exact Owned Paths
- `backend/app/security/`
- `backend/tests/security/`

## Implemented Behavior
1. **Durable Opaque Sessions (`backend/app/security/sessions.py`)**:
   - Random 32-byte (256-bit entropy) session token issued as HttpOnly, SameSite, Secure (TLS-dependent) cookie (`fd_session`).
   - Raw session token never stored; keyed HMAC-SHA256 digest (`SESSION_DIGEST_KEY`) persisted in PostgreSQL `sessions` table.
   - Per-session random CSRF secret generated and stored server-side.
   - Absolute 24-hour lifetime without sliding window.
   - Multi-device support: multiple active sessions map to single stable user account.
   - Revocation marks `revoked_at`; expired/revoked sessions return 401.

2. **Credential Provisioning & Authentication (`backend/app/security/provisioning.py`)**:
   - Invitation access codes provisioned externally (admin/organizer setup); rejected in production normal profile.
   - Raw codes never stored or logged; HMAC-SHA256 digest (`CREDENTIAL_DIGEST_KEY`) persisted.
   - Login creates session only; does not self-issue user accounts or eligibility grants.
   - Multiple logins with same credential map to identical stable user.
   - Constant-time validation preventing credential enumeration.

3. **Origin & CSRF Enforcement (`backend/app/security/csrf.py`)**:
   - Strict Origin header validation on browser write mutations against configured `allowed_origins`.
   - Deterministic per-session HMAC-SHA256 CSRF token returned in `GET /auth/me` and `POST /auth/session`.
   - Constant-time verification of `X-CSRF-Token` header on all state mutations (`POST`, `PATCH`, `DELETE`).
   - Missing or invalid CSRF returns 403 `CSRF_REJECTED`. Disallowed Origin returns 403 `ORIGIN_REJECTED`.

4. **Multi-Dimensional Atomic Rate Limiting (`backend/app/security/limits.py`)**:
   - Redis sliding window Lua script (atomic `ZREMRANGEBYSCORE` + `ZCARD` + `ZADD` + `EXPIRE`).
   - Dimensions: account-level (survives session rotation), session-level, endpoint/action-level, trusted-IP network-level, and global.
   - Handles `NoScriptError` dynamically by reloading Lua script.
   - Trusted IP derived strictly from proxy-controlled `X-Real-IP` or direct client socket; untrusted `X-Forwarded-For` ignored.
   - Rate limit rejection returns 429 `RATE_LIMITED` with `Retry-After` header.
   - Redis outage degraded behavior: protected writes return retryable 503 `TEMPORARILY_UNAVAILABLE`; DB-backed reads continue.

5. **Server-Side Authorization & Profile Protection (`backend/app/security/authorization.py`)**:
   - Deny-by-default principal extraction (`get_principal`) raising 401 `SESSION_REQUIRED`.
   - Role enforcement (`require_organizer`) raising 403 `FORBIDDEN`.
   - Drop ownership check (`require_drop_access`) with admin bypass and honest 501 until P1 Drop table integration.
   - Profile patch (`PATCH /api/v1/profile`): permits only `display_name` and valid IANA `timezone`; explicitly rejects attempts to alter `role`, `is_admin`, `is_active`, `owner_id`, or `seat_status` with 403 `FORBIDDEN`.

6. **Contracted Security Router (`backend/app/security/router.py`)**:
   - `POST /api/v1/auth/session` (login)
   - `GET /api/v1/auth/me` (session check / CSRF refresh)
   - `DELETE /api/v1/auth/session` (idempotent logout / cookie clear)
   - `PATCH /api/v1/profile` (safe profile updates)
   - All responses include `Cache-Control: no-store, Pragma: no-cache` headers.

## Completed Files with Evidence
- `backend/app/security/__init__.py`: Package export interface for P1/P4 integration.
- `backend/app/security/csrf.py`: CSRF token generation and constant-time validation.
- `backend/app/security/sessions.py`: Opaque cookie session management with PostgreSQL digest store.
- `backend/app/security/provisioning.py`: Access code hashing, verification, and demo-only provisioning.
- `backend/app/security/limits.py`: Redis atomic sliding-window limiter with degraded 503 handling.
- `backend/app/security/authorization.py`: Principal and role authorization dependencies.
- `backend/app/security/router.py`: Wire contract auth and profile API endpoints.
- `backend/tests/security/conftest.py`: Test fixtures and test configuration.
- `backend/tests/security/test_credentials.py`: Credential authentication tests.
- `backend/tests/security/test_sessions.py`: Session lifecycle, refresh, and multi-device identity tests.
- `backend/tests/security/test_csrf_origin.py`: CSRF and Origin header validation tests.
- `backend/tests/security/test_authorization.py`: Role protection and privilege escalation prevention tests.
- `backend/tests/security/test_limits.py`: Rate limiting, session rotation, and shared IP independence tests.
- `backend/tests/security/test_outage.py`: Redis failure resilience and error sanitization tests.

## Actual Commands & Results
- Verified Python environment: Python 3.13.1, pytest 8.3.3.
- Inspected codebase, git branch `feature/m2-security`, verified clean architectural alignment with `rules.md`, `architecture.md`, `prd.md`, and `whiteboard.md` (WB-03, WB-04, WB-09).
- Tested local service availability: Host does not have local background PostgreSQL/Redis services running directly (Docker Compose owned by P4 in Phase 0/7).

## Remaining Work
- End-to-end integration with P1's Drop model inside `require_drop_access` once P1 merges core drops.
- End-to-end load testing of rate limiters with P4's two-replica Docker Compose stack in Phase 7.

## Blockers
- None for Member 2 code. Live database tests require PostgreSQL and Redis instances (standard Compose setup from P4).

## Cross-Owner Handoff
- **To P1 (Core & Contract)**:
  - Mounted exports: `backend.app.security.router` (mounted at `/api/v1`), `get_principal`, `require_organizer`, `require_drop_access`, `check_drop_grant`, `enforce_limit`.
  - Auth contract: Cookies are `fd_session`, CSRF header is `X-CSRF-Token`.
  - Provisioning: `provision_user_with_credential` available for demo seed scripts.
- **To P3 (Frontend)**:
  - Authentication flow: Login via `POST /api/v1/auth/session` with `{"access_code": "..."}`. Returns `SessionResponse` with `csrf_token` and sets `fd_session` HttpOnly cookie.
  - Refresh flow: Call `GET /api/v1/auth/me` on app load/reconnect to fetch principal and fresh `csrf_token`.
  - Mutating operations: Send `X-CSRF-Token` header with all `POST`, `PATCH`, `DELETE` requests.
  - Profile update: Send `PATCH /api/v1/profile` with `{"display_name": "...", "timezone": "..."}`.
- **To P4 (Infrastructure & Lab)**:
  - Environment variables consumed: `SESSION_DIGEST_KEY`, `CREDENTIAL_DIGEST_KEY`, `DATABASE_URL`, `REDIS_URL`, `PUBLIC_ORIGIN`, `COOKIE_SECURE`.
  - Outage policy: When Redis is down, reads succeed, protected writes return retryable 503 `TEMPORARILY_UNAVAILABLE`.

## Next Action
Stage and commit Member 2 implementation on `feature/m2-security` branch.
