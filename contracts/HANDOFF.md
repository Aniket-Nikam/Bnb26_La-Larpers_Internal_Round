# Integrated implementation handoff / wire contract v1.0


Current integration supersedes the bootstrap-only status notes below. M1/M2/M3/M4
are integrated on main; auth/profile and lab routes are implemented. Session cookie
is fd_session. All imports run as app.* from backend/. Security hooks are sync and
return shared Principal DTOs; protected mutations enforce Origin and CSRF before
domain operations. Redis limits are shared across replicas. Migration head is
d3f100000001. Generated frontend types live in frontend/src/lib/api/generated.ts.
Lab RunReport has an optional additive policy_comparison mapping for matched policy
outcomes; the top-level report describes LOTTERY in comparison runs.

See ../INTEGRATION_REPORT.md and ../README.md for current commands and evidence.
Historical owner handoff notes below describe M1 before this authorized integration.

Source: docs/architecture.md. Canonical docs remain in docs/ per user's instruction.
No second API or frontend is created. Old TypeScript ingress experiments are preserved.
The blank template is misnamed docs/memory.md; root memory.md is now active.

## Verified bootstrap commands

Run backend commands from backend/ with environment configured:

```
uv sync --frozen --python 3.12
uv run alembic upgrade head
uv run alembic check
uv run python -m app.core.export_contract
uv run python -m app.core.export_examples
uv run pytest -q
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The API process command was verified with TestClient and a real socket process;
liveness/readiness/public reads, worker --once and graceful shutdown passed. Configuration export does not
require live services: APP_PROFILE=test is sufficient. Mutations require stable
SEED_ENCRYPTION_KEY, base64 of 32 random bytes. Normal additionally requires HTTPS,
Secure cookies and non-placeholder digest keys. No secrets/default keys are shipped.

Contract generation, from contracts/:

```
npm ci --ignore-scripts
npm run generate
npx tsc --noEmit --skipLibCheck generated.ts
```

`npm run generate:frontend` uses the SAME verified generator/options and targets
frontend/src/lib/api/generated.ts. P3 owns running that command after adopting the
checkpoint. contracts/generated.ts is the checked generated artifact, not a client.
Examples are schema fixtures only, never measured runs or runtime fake responses.

## Imports and models / named handoffs

- P2: exclusive implementation ownership of backend/app/security after bootstrap.
  Replace deny-by-default hooks in authorization.py and limits.py and router.py.
  Keep get_principal(request), require_organizer(request),
  require_drop_access(principal, drop_id), enforce_limit(request, principal, action).
  Principal is app.core.schemas.Principal. Hooks can be sync or async when consumed
  as dependencies; require_drop_access must remain synchronous for domain guard.
  get_principal must validate credential/session and enforce CSRF/Origin for writes;
  limits must degrade sensitive writes on Redis failure. Expose SECURITY_IMPLEMENTED
  only after this works. Limiter actions: entry, confirmation, status, organizer.
  Models: User, AccessCredential.digest, Session.token_digest/credential_id/
  csrf_secret, EligibilityGrant. Generic idempotency excludes login/token responses.
- P4: exclusive implementation ownership of backend/app/lab and memory.md after
  bootstrap. Replace lab/router.py; keep router and LAB_IMPLEMENTED exports. Consume
  core.schemas.Run* DTOs and persistence.models.LabRun as shared API authority.
  LabRun has owner_id, config/progress, safe error/report, report_path, timestamps,
  and one-active-job partial unique index. Inspected remote P4 runner uses its own
  artifact journal pending LabRun adoption; no conflicting P4 implementation imported.
- P3: generate TypeScript from committed OpenAPI; exact snake_case response shapes.
- P4 infrastructure: use python -m app.allocation.worker, python -m alembic upgrade
  head, app.main:app from backend cwd. Environment names match P4 Compose branch.

All 14 record types share Base.metadata; initial Alembic revision is b3194d72d2b4.
Reservation composite FKs bind entry/user/drop and slot/drop. Partial indexes enforce
active slot/user uniqueness; one lifetime reservation per entry prevents reoffers.
Exactly capacity slots is a transactional publication invariant, checked by tests.
No startup create_all. All schema changes stay with P1.

Acknowledgements by P2/P4 are pending, not fabricated. Auth/login, real limits,
lab orchestration, frontend/browser integration and measured load remain owner
requirements. Never enable production overrides to substitute for them.


## Final M1 checkpoint

Updated UTC: 2026-10-03T17:53:42.031585Z. Core implementation commit: `f644645ac0ae8390727871cd657a09c9b6e5dcbb`.
Branch: `M1`, based on main `7eedd2f`; bootstrap `e43f871`. Contract: `v1.0`.
Alembic head: `c2f4a1230001`. No main/M2 merge; user explicitly required M1-only push.
Central memory remains the bootstrap snapshot owned by P4; current M1 truth is in
progress/person-1.md and this handoff. No integrated-app gate or human review claimed.

### Implemented paths and behavior

| Path | Implemented |
| --- | --- |
| backend/app/core/ | Profile/secret/bounds config, safe errors/request IDs, UTC wall clock, durable scoped idempotency, pagination, complete wire DTOs and contract export |
| backend/app/persistence/ | Single 14-record model system, READ COMMITTED psycopg pools, composite FKs and partial uniqueness |
| backend/alembic/ | Ordered complete foundation and sealed immutable snapshot/ranking migrations; no startup create_all |
| backend/app/drops/ | Public metadata, owned drafts/descriptive edits, existing-account grants, publication, saved unique entries, own history/receipts/state, cancel, metrics/audit/pseudonymous CSV |
| backend/app/allocation/ | AES-GCM seed protection, exclusive freeze, canonical HMAC ranking, atomic publication, offers/confirm/expiry, exact fixed-rank promotion, bounded durable worker, demo-only FCFS |
| backend/app/audit/ | Safe transition facts, pending/published compressed proof, independent bounded standard-library verifier |
| backend/app/main.py | Fixed routers, request/body handling, explicit dependency readiness/capabilities and safe error mapping |
| backend/tests/core/ | 27 actual PostgreSQL/HTTP/core-integrity checks and process-crash/CLI tests |
| contracts/ | OpenAPI 33 paths, v1.0, validated state/error/proof/lab fixtures, locked generation tooling and compiled generated TypeScript |
| backend/app/security/, backend/app/lab/ | Bootstrap skeletons only; implementation handed to P2/P4, fail explicitly with NOT_IMPLEMENTED |

### Executed verification

Environment: Linux, Python 3.12.14, PostgreSQL 18.6 (real local server on 127.0.0.1:55432),
UTF-8 databases. Main test DB fairdrop_m1_test; fresh migration DB fairdrop_m1_fresh_test.
Redis was unavailable in this checkout; degradation was checked, real limiter Lua was
NOT run. No Docker, browser, measured multi-replica or 50k-concurrency claim is made.

Commands executed from backend/ (DATABASE_URL was set to the applicable local test DB):

```
uv sync --frozen --python 3.12
uv run alembic upgrade head
uv run alembic check
uv run alembic downgrade base  # only the fresh disposable DB
uv run alembic upgrade head
uv run alembic check
uv run pytest -q              # 27 passed, 1 deprecation warning
uv run ruff check app alembic tests/core
uv run ruff format --check app alembic tests/core
uv run python -m app.core.export_contract
uv run python -m app.core.export_examples
uv run python app/audit/verifier.py ../contracts/examples/proof-published.json --public-entry-id fd_example
```

Actual subprocess commands executed with test configuration:

```
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 58001
.venv/bin/python -m app.allocation.worker --once
```

A managed HTTP smoke fetched /api/health/live, /api/health/ready and /api/v1/drops,
then verified graceful SIGTERM logs and termination. Uvicorn intentionally re-raises
SIGTERM after graceful shutdown; requiring only exit 0 was an incorrect initial smoke
assertion, corrected and rerun. Worker restart after SIGKILL uses the actual entrypoint.

Commands executed from contracts/:

```
npm ci --ignore-scripts
npm run generate
npx tsc --noEmit --skipLibCheck generated.ts
npm run generate:frontend
```

The exact generate:frontend script was executed and compiled in a disposable copy
with the expected frontend directory structure. No P3 source was edited. P3 runs it
in the integrated checkout to regenerate their file.

Tests cover same-account concurrency with same/different keys, simulated devices,
receipt/organizer/reservation ownership, committed retry recovery, entry-versus-close
actual lock waits, late entry/confirmation after lock waits, concurrent draw triggers,
empty/undersubscribed/exhausted draws, capacity/FKs/active owner uniqueness, both legal
confirmation/expiry outcomes, exact promotion, bounded missing-offer recovery, real
SIGKILL mid-draw/offer/promotion, same-input ranking despite changed order, proof
reproduction/tampering/privacy, UTC/Z output, missed schedules and safe DB outages.

### Remaining owner dependencies / limits

- P2: real session/login/CSRF/Origin/limiter hooks and router. Tests use an explicitly
  isolated security adapter to verify P1's domain invariants; that is not real login,
  cookie multi-device or limiter evidence. With current stubs, protected APIs remain
  closed and readiness says protected_writes=false. No production bypass is shipped.
- There are two incompatible remote M2 implementations. `M2` expects backend.app
  imports, async sessions, uppercase settings, AuthContext, credential_digest,
  is_active fields and fd_session; this M1 contract uses app imports, synchronous
  psycopg, Principal DTO and digest/credential-linked sessions. `codex/m2-security`
  expects repository protocols, csrf_digest and fairdrop_session and has no router.
  Neither is silently adopted. User explicitly declined either merge. P2/P1 must
  coordinate the shared adapter/model contract before integration.
- P3: regenerate types and verify the real browser login-to-confirmed-ticket journey.
  The newer remote frontend main commit was not merged or edited.
- P4: adopt LabRun/typed report schemas, worker/migration commands and .env/Compose;
  integrate provisioning, run real Redis/replica/load/lab/browser tests, maintain
  central memory. Existing P4 remote code was inspected read-only, not merged.
- Reproducible draw does not prevent an operator searching seeds/selectively aborting.
  FCFS proof validates manifest and complete ranks, not independent admission history.
  Worker restart evidence does not establish full-host/storage-loss recovery.
- Population/capacity ceilings are configured bounds, not measured throughput claims.
  The core suite is a small correctness workload. No human review was recorded.

Production/demonstration integration remains pending; all P1-owned domain handlers
are implemented. Keep stable secret configuration across process restarts. Demo/test
reset fixtures must never target a normal database. Full application release still
requires the other owners and their real integration checks.
