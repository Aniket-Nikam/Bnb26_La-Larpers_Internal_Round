# P2 security integration contract

Status: security policy and repository protocols are implemented on the P2
branch. FastAPI routes and real PostgreSQL/Redis adapters remain blocked on P1's
bootstrap; no substitute database or fake authenticated principal is provided.

## P1 shared-model fields required

`User`: `id`, random `public_id`, `role` (`participant|organizer|admin`),
`display_name`, `timezone`.

`AccessCredential`: `id`, `user_id`, unique indexed keyed `digest`, `issued_at`,
nullable `expires_at`, nullable `revoked_at`. Raw access codes are never stored.

`Session`: `id`, `user_id`, unique indexed `token_digest`, `csrf_digest`,
`created_at`, absolute `expires_at`, nullable `revoked_at`. The opaque cookie is
never stored. The CSRF value is deterministically derived from that cookie with a
purpose-separated HMAC and can therefore be returned by `GET /auth/me` after a
refresh while only digests remain in PostgreSQL.

`EligibilityGrant` and drop/entry ownership stay in P1's model. P2 needs adapter
methods matching `protocols.py`; accepted entries must not be deleted or reranked
when a credential/session is later revoked.

## Bootstrap wiring

P1 creates PostgreSQL adapters for `CredentialRepository`, `SessionRepository`,
and `DropAccessRepository`, plus a redis-py adapter whose `eval` delegates to
Redis. At application startup instantiate the services and call
`configure_security_dependencies(...)` exactly once. The stable helpers are:

- `get_principal(request)`
- `require_organizer(request)`
- `require_drop_access(principal, drop_id)`
- `enforce_limit(request, principal, action)`
- `enforce_login_limit(request, access_code)`

P1 retains ownership of `backend/app/main.py`, shared models/migrations, response
schemas, central error mapping, and OpenAPI. P2 will add `security.router` only
against those exact committed schemas/adapters; returning fabricated success or
creating parallel ORM tables is prohibited.

## Route sequence

`POST /api/v1/auth/session`: require exact Origin; enforce login limit before
credential verification; verify credential; insert durable session; set cookie
with `SessionCookiePolicy`; return principal, derived CSRF, expiry, server time;
add `Cache-Control: no-store`. Unknown/expired/revoked credentials share one safe
error.

`GET /api/v1/auth/me`: authenticate cookie from PostgreSQL; return the same
principal, derived CSRF, absolute expiry and server time; no-store.

`DELETE /api/v1/auth/session`: require Origin and derived CSRF; revoke current
session if present; clear the cookie; an authorized retry is 204.

`PATCH /api/v1/profile`: authenticate, require Origin/CSRF, allow only
`display_name` and an IANA timezone, persist through the shared repository, and
return the contracted response with no-store.

Domain routes authenticate first, enforce server ownership, validate Origin/CSRF
for writes, then call the limiter before performing protected work. A frontend
route guard is never authorization.

## Limiter policy

The Lua script checks all dimensions and increments them in one Redis operation.
All keys use one Redis cluster hash tag. Credential/network/account values are
keyed digests; raw access codes and addresses never appear in Redis keys.

| Action | Account | Session | Network | Global |
| --- | ---: | ---: | ---: | ---: |
| Login | credential 5/60s | — | 100/60s | 2000/60s |
| Entry write | 5/10s | 5/10s | 200/10s | 2000/10s |
| Confirmation write | 5/10s | 5/10s | 200/10s | 2000/10s |
| Status read | 30/10s | 30/10s | 1000/10s | 5000/10s |

Network/global values are initial P2 policy and require P4 shared-IP/load evidence
before tuning. They remain identical for LOTTERY and FCFS_DEMO. Account limits
remain stable when sessions or source addresses rotate.

If Redis fails, authenticated status reads return a degraded allowed decision;
entry/confirmation/login writes raise retryable `TEMPORARILY_UNAVAILABLE`.
Never fall back to a per-process limiter. Redis recovery resumes shared limits;
PostgreSQL sessions and accepted domain records remain authoritative.

## Proxy and cookie policy

Only configured trusted proxy CIDRs may supply `X-Forwarded-For`; direct clients
cannot select limiter identity. The resolution algorithm walks from the trusted
peer toward the first untrusted address. P4's gateway should be configured as an
exact `/32` where possible.

Session cookies are HttpOnly, SameSite=Lax, Path=/, and have the 24-hour absolute
max age. Normal profile requires HTTPS and Secure cookies. `demo`/`test` may use
the documented local HTTP exception with `COOKIE_SECURE=false`.

## Existing incompatible proof-of-work/JWT files

The root `services/` and `middleware/` prototype uses an insecure JWT fallback,
in-memory PoW state, and bot-score fields. It is not the canonical P2 path and
must not be mounted into FairDrop. P2 has not deleted another member's files.
Default FairDrop does not use PoW, IP uniqueness, suspicion weighting, or harness
human/bot labels to alter accepted-entry ranking.
