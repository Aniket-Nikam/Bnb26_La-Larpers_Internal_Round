# FairDrop operations and attack-lab status

This branch contains the Member 4 infrastructure, bounded lab runner, metric
aggregation, and real-HTTP k6 scenario foundation. It does **not** yet contain a
runnable integrated FairDrop application: the P1 backend/worker/migrations and
contract, P2 auth/provisioner, and P3 frontend are not present on the base branch.
The preflight script fails explicitly until those integration dependencies land.

No benchmark or capacity result is claimed by this repository state.

## Implemented Member 4 foundation

- `compose.yaml`: persistent PostgreSQL, Redis, two API replicas, migration job,
  durable worker process, static frontend build, and same-origin Nginx gateway.
- `infra/compose.demo.yaml`: isolated demo override and runner profile. The normal
  file forces lab, FCFS, fixture seeding, and development mocks off.
- `backend/app/lab/`: strict allowlist/caps, one-active-run enforcement, atomic
  run-state persistence, safe subprocess argument arrays, trial lifecycle,
  stop/timeout behavior, partial artifact retention, and PRD metric calculations.
- `tests/performance/scenarios/`: authenticated cookie/session/CSRF workloads for
  every contracted scenario. Shared-IP and service-failure workloads refuse to
  masquerade as evidence without controlled topology/injection confirmation.
- `scripts/`: dependency preflight, allowlisted demo-only failure injection, and
  explicit destructive demo reset.

## Checks that work now

From the repository root:

```powershell
python -m unittest discover -s backend/tests/lab -p "test_*.py" -v
python -m compileall -q backend/app/lab backend/tests/lab
git diff --check
```

Compose structure can be validated with nonsecret placeholders before `.env`
exists. A real start is intentionally blocked until teammate Dockerfiles and
entrypoints exist:

```powershell
$env:POSTGRES_PASSWORD='placeholder'
$env:DATABASE_URL='postgresql+psycopg://fairdrop:placeholder@postgres:5432/fairdrop'
$env:REDIS_URL='redis://redis:6379/0'
$env:PUBLIC_ORIGIN='https://fairdrop.example.invalid'
$env:SESSION_DIGEST_KEY='placeholder'
$env:CREDENTIAL_DIGEST_KEY='placeholder'
$env:SEED_ENCRYPTION_KEY='placeholder'
docker compose -f compose.yaml config --quiet
docker compose -f compose.yaml -f infra/compose.demo.yaml --profile lab config --quiet
```

## Integrated startup (blocked at this checkpoint)

After P1/P2/P3 land their owned dependencies:

1. Copy `.env.example` to `.env`; replace every `CHANGE_ME` value and set the
   intended profile/origin. Do not commit `.env` or private credential fixtures.
2. Run `powershell -File scripts/preflight.ps1 -RequireLoadTools`.
3. Normal profile: `docker compose --env-file .env up --build -d`.
4. Demo profile: use a demo/test `.env`, then run
   `docker compose -p fairdrop-demo --env-file .env -f compose.yaml -f infra/compose.demo.yaml --profile lab up --build -d`.
5. Inspect process liveness at `/api/health/live` and dependency capabilities at
   `/api/health/ready`. Redis degradation must preserve safe DB-backed reads;
   PostgreSQL failure makes authoritative operations unavailable.

These commands are wiring targets, not yet verified startup claims. The missing
paths are listed by `scripts/preflight.ps1`.

## Private workload data

P2's provisioner must write the actor-to-credential fixture beneath
`private/lab/`; see `tests/performance/README.md` for its shape. Raw access codes
remain restricted to that ignored directory and the runner mount. Reports must
contain actor/credential counts, never raw access codes, cookies, CSRF values, or
unrevealed seeds.

Provisioning and database population happen before measured entry traffic. A
population of 50,000 rows is not evidence of 50,000 concurrent users.

## Failure injection and reset safety

Only the host-side script can control the allowlisted `worker` or `redis`
service, and only for a `demo` or `test` `.env`:

```powershell
powershell -File scripts/failure_injection.ps1 -Service worker -Action restart -IsolatedDemoConfirmed
```

Destructive reset requires an explicit flag and targets only the fixed
`fairdrop-demo` Compose project:

```powershell
powershell -File scripts/demo_reset.ps1 -IUnderstandThisDeletesDemoData
```

Process-restart evidence is not backup/restore or host-data-loss evidence.

## Current integration blockers

- P1: shared `LabRun` persistence/transaction model, mounted FastAPI app/router
  interface, worker/migration entrypoints, authoritative report reconciliation,
  FCFS comparator, OpenAPI/examples, and backend Dockerfile/lock.
- P2: organizer dependency, CSRF/Origin enforcement, shared limiter behavior,
  private provisioning utility, and Redis degradation contract.
- P3: production frontend build/Dockerfile and stable accessible Playwright
  locators.
- Environment: k6 and Make are not installed on this Windows host. Docker and
  Compose are available; k6 execution and real traffic remain NOT RUN.

The central `docs/memory.md` is still the untouched template because P1 has not
performed the bootstrap handoff. Member 4 status is recorded separately in
`progress/person-4.md`.
