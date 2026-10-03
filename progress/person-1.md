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
