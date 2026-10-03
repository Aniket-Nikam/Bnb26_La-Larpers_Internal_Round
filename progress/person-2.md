# Member 2 progress

- Updated UTC: 2026-10-03T17:15:22Z
- Branch: `codex/m2-security`
- Base commit: `7eedd2f`
- Scope: provisioned credentials, durable opaque sessions, CSRF/Origin,
  authorization, shared abuse-control policy, privacy, and security handoff.
- Current phase: pre-bootstrap P2 security foundation; P1 bootstrap NOT DONE.

## Implemented on this branch

- Purpose-separated HMAC-SHA256 digests for credentials, opaque session cookies,
  CSRF material, limiter dimensions, and credential-attempt keys.
- Private credential provisioner that generates high-entropy access codes, stores
  only keyed digests, requires an existing stable user, records issue/expiry via
  the P1 repository protocol, and rejects demo fixtures in normal mode.
- Credential verification with one indistinguishable error for unknown, expired,
  and revoked credentials. Login never creates a user, role, or eligibility grant.
- PostgreSQL-oriented session service over P1 adapter protocols: random opaque
  cookie, only digest persisted, per-session derived CSRF, absolute 24-hour
  expiry, revocation, repeat logout, refresh/service-restart recovery, and stable
  identity across multiple sessions.
- Strict profile allowlist for display name and IANA timezone; role/grant/owner/
  seat fields are rejected.
- Exact Origin and session-bound CSRF checks; HttpOnly/SameSite=Lax/Path=/ cookie
  policy; normal-mode HTTPS/Secure enforcement with explicit demo/test exception.
- Deny-by-default participant/organizer/admin authorization, organizer ownership,
  participant drop access, and 404 non-disclosure for foreign private resources.
- Trusted-proxy source resolution; untrusted `X-Forwarded-For` cannot select a
  limiter identity.
- Atomic Redis fixed-window Lua contract across account, session, network and
  global dimensions; required 5/10s entry, 5/10s confirmation and 30/10s status
  account budgets; stable account quota across session rotation; keyed network
  and credential-attempt identifiers; meaningful Retry-After.
- Redis outage policy: safe authenticated reads continue as degraded; login,
  entry and confirmation writes fail retryably with 503; no in-process fallback.
- Stable dependency helpers and a detailed P1/P4 integration contract.

## Actual checks

`python -B -m unittest discover -s backend/tests/security -p "test_*.py" -v`
passes 28 tests covering all independently testable policy paths.

`git diff --check` passes. Python modules imported successfully under Python
3.13.14. Docker CLI is installed, but the Docker Desktop Linux engine was not
running, so real Redis integration was NOT RUN.

The concurrency test uses a thread-safe behavioral backend to verify shared
budget semantics; it is not evidence that the Lua script executed in Redis.

## Required cross-owner handoff

- P1: implement the fields and repository adapters in
  `backend/app/security/INTEGRATION.md`; commit migrations, FastAPI response
  schemas, central error mapping, OpenAPI, and `main.py` wiring. Then hand the
  security router skeleton to P2 for exact route implementation.
- P4: use the documented limiter thresholds unchanged across LOTTERY/FCFS runs;
  configure the gateway as the only trusted proxy; measure shared-IP admission;
  wire private demo provisioning without exposing raw credentials in reports.
- P3: use same-origin credentialed requests, keep access codes/session/CSRF out
  of persistent browser storage, and reconcile session state on 401/429/503.

## Not yet verified

- Real FastAPI routes and cookie headers, because P1 schemas/app are absent.
- Real PostgreSQL persistence, replica/restart behavior, and ownership queries.
- Real Redis Lua atomicity, two-API shared state, outage and recovery.
- Browser session/CSRF flow and P4 shared-IP/load scenarios.

The root `services/`/`middleware/` JWT/PoW prototype is not mounted into this
implementation: its insecure fallback, in-memory state, and bot-score semantics
conflict with the canonical architecture. Those files were preserved because
they are outside P2's assigned backend path. Human whiteboard review remains
PENDING.
