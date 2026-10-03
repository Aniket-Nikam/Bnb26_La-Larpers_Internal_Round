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

## Offers/confirmation/expiry/worker feature — 2026-10-03 UTC

Previous ranking commit: 20775f3. Implemented authoritative OFFERED reservations,
owning-identity confirmation and replay, fresh DB wall clock after ordered locks,
expiry and exact next-rank promotion, one-lifetime-offer-per-entry, atomic cursor/
audit/ownership writes, empty/exhausted/undersubscribed completion and <=100-change
reconciliation batches. Worker discovers lifecycle/ranking/offers from PostgreSQL,
handles interruptions, accepts SIGTERM/SIGINT and supports --once verification.
No Redis TTL dependency; normal worker needs a stable valid AES-GCM key.

Checks executed: pytest -q 18 passed on real PostgreSQL. Tests include concurrent
confirm/replay, cross-owner denial, capacity/current owner uniqueness, cross-drop
foreign-key rejection, late confirmation after lock wait, timely confirmation whose
commit passes expiry while worker waits, exact original-rank promotion, unused-seat
completion, bounded missing-offer recovery, real SIGKILL of subprocesses during draw/
offer/promotion and actual python -m app.allocation.worker --once restart recovery.
ruff passed. API clock tests use only test fixtures to move deadlines; production
policy fields remain locked. Full real login/browser/limiter path still awaits P2/P3.
Next: public-safe proof, independent standalone verifier, then isolated FCFS comparator.

## Public proof / independent verifier feature — 2026-10-03 UTC

Previous allocation commit: f9d4abc. Implemented pending/published proof with no seed
before complete ranking, pseudonymous manifest/ranks/scores only, compressed delivery,
independent bounded stdlib verifier/CLI and participant inclusion check. Optimized CSV
export to one joined query rather than per-entry projections. Added valid proof fixtures.
Verifier checks seed/manifest commitments, scores, unique complete ranks, exact ordering
and supplied participant ID. Claims reproducible/auditable only; operator seed search /
selective cancellation remain possible. Without participant ID, inclusion is not claimed.

Executed full core suite: 20 passed on PostgreSQL. Additional focused proof/foundation
rerun after examples/compression assertion: 5 passed. CLI successfully verified committed
proof fixture; OpenAPI export, schema fixtures, TypeScript generation+compile and ruff
passed. Tests mutate commitments/ranks/scores/inclusion, check private IDs/names absent,
verify canonical same-input ranking across changed order, and check actual gzip delivery.
Next: isolated FCFS_DEMO sharing all domain defenses. No production auth bypass added.

## Isolated FCFS comparator feature — 2026-10-03 UTC

Previous proof commit: c65bc3e. Implemented demo-only exclusive admission sequence,
immediate offers/waitlist, OPEN-window expiry/promotion/new admission, original-order
freeze/ranking, shared confirmation and ownership protections. FCFS proof explicitly
has null seed/commitment/scores; verifier checks manifest/rank completeness while
stating that admission order is not independently established by HMAC evidence.
Default lottery keeps compatible entry locks and request-independent scores.

Executed: pytest -q 23 passed on PostgreSQL, ruff passed. New checks cover rejection
outside demo even with an enable flag, invalid normal profiles, admission-order offers,
concurrent duplicates, expiry during OPEN, refusal to cancel after offers, empty-slot
new admission, null lottery fields, ordered frozen proof and confirmed completion.
Remote M2 branches and new origin/main appeared during this checkpoint. Next: inspect
those read-only, resolve shared-model/interfaces against real owner code and verify
integrated security journey if an adoptable P2 implementation now exists.

## Final core hardening feature — 2026-10-03 UTC

Previous FCFS commit: 3536139. Fixed UTC/Z wire normalization for offset-bearing
inputs and database clocks (local PostgreSQL default was Asia/Kolkata). Validated
canonical origins, bounded pools/ticks and normal placeholder keys; bounded public
ID inputs; aligned FCFS CSV waitlist status; prevented existing demo drops from
allocation/public proof in normal profile. Added missed-schedule reconciliation,
explicit correlated DB-outage checks and direct composite-FK mutation rejection.

Executed: pytest -q 27 passed on real PostgreSQL 18.6 / Python 3.12.14. Upgrade/check
on fresh UTF-8 DB, downgrade base, upgrade head and check all passed. Actual socket
API startup/live/ready/public read, worker --once and graceful API SIGTERM passed.
Initial shutdown smoke incorrectly required exit 0; installed Uvicorn deliberately
re-raises SIGTERM after graceful shutdown. Corrected the smoke to verify shutdown
completion and exit 0 or -SIGTERM, then reran successfully. Both contract-generation
scripts passed; generate:frontend ran in a disposable frontend tree (P3 untouched),
with TypeScript compilation. Schema/examples export, ruff check and format --check
passed. One known Starlette/httpx deprecation warning remains, without test failures.

User explicitly instructed: push M1 only, do not merge M2 or change main. Both remote
M2 implementations remain unmerged. Real authenticated cookie/CSRF/Redis integration,
frontend browser journey, lab and measured multi-replica/load evidence remain pending
with their owners. P1-owned domain handlers have no NOT_IMPLEMENTED stubs; only
security/lab stubs remain, fail closed, and readiness discloses unavailable writes.
