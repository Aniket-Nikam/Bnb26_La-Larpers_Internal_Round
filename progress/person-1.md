# M1 / P1 implementation progress

Branch: M1 from main 7eedd2f. Foundation in progress, not integrated.
Owned: backend core/persistence/drops/allocation/audit, main, dependencies, migrations,
contracts, this record. Security/lab skeletons only during bootstrap.
No checks or human review claimed yet. P2 auth/limiter and P4 lab remain dependencies.

## Foundation feature checkpoint — 2026-10-03 UTC

Implemented shared ORM (14 records), Alembic b3194d72d2b4, complete typed wire DTOs,
31 route paths, safe errors/request IDs/body cap, real health dependency checks,
closed security hooks, lab stubs, schema fixtures and TypeScript tooling.
Executed: uv sync --frozen --python 3.12; alembic upgrade head and check;
python -m app.core.export_contract/export_examples; pytest -q (3 passed on real
PostgreSQL 18 UTF-8); npm ci, npm run generate and tsc --noEmit (passed).
Initial SQL_ASCII test database failed dialect initialization; corrected disposable
setup to UTF-8. pytest import path fixed before pass. Starlette emits a deprecation
warning for the baseline httpx adapter; no functional test failure.
Handoff: contracts/HANDOFF.md. Security/lab implementation now belongs to P2/P4.
Next: P1 domain routes, durable entry/idempotency and PostgreSQL race verification.

## Durable entry/domain feature — 2026-10-03 UTC

Bootstrap commit: e43f871. Implemented public discovery/detail; owner-guarded drafts,
pre-existing-account grants/removal; publication locks and exactly-capacity slots;
AES-GCM protected committed seed; cancellation; own receipt/history/state; safe audit,
CSV export and derived inventory. Durable scoped operation claims use PostgreSQL
ON CONFLICT+row locks, payload fingerprints and domain references, never credentials.
Concurrent LOTTERY admissions hold compatible FOR SHARE; no drop counter upgrades.
Population bound follows <=50000 locked grants; composite grant FK binds identity.
Public IDs have random 192-bit material and fd_ prefix to keep CSV cells inert.

Checks executed: pytest -q, 6 passed on real PostgreSQL 18 (including 16 concurrent
same-account HTTP operations, same/different keys; single entry/audit; late recovery;
new late denial; authorization/privacy; publication/grant locks; cancellation).
ruff passed; OpenAPI export and generated TypeScript compile passed. One failed
eligibility-removal check exposed an ambiguous ORM join; fixed the explicit user FK.
Security in these tests is an EXPLICIT TEST-ONLY adapter, not real P2 login/CSRF/limits.
Real login/browser integration remains BLOCKED on P2/P3; deny-by-default remains live.
Next: exclusive close/freeze, immutable ranking publication and draw recovery.

## Close/freeze/ranking feature — 2026-10-03 UTC

Previous domain commit: 803e068. Implemented exclusive closure, fresh statement
snapshot after waiting for admissions, all-accepted manifest (later revocation does
not subtract entries), one run/seed, unlocked canonical HMAC computation, atomic
complete rank publication and safe recoverable checkpoint. Migration c2f4a1230001
seals FrozenEntry membership, prohibits published rank mutations/draw reset and
cursor rewind; app models have snapshot_sealed. Shared migration goes only through P1.

Checks: upgrade head and alembic check passed; pytest -q 11 passed on real PostgreSQL.
Evidence includes actual pg_stat_activity lock wait during entry-vs-close, late entry
waiting past deadline, eight concurrent triggers/computations using one draw, exact
canonical seed/manifest/HMAC order, later grant revocation retained, immutable proof
rows, interrupted publication rollback/retry with original seed/run, empty manifest.
ruff passed. No human review claimed. Offers/proof HTTP still pending at this checkpoint.
Next: reservation/confirmation/expiry/promotion and durable worker reconciliation.
