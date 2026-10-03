# Integrated main verification

Verified 2026-10-03 UTC / 2026-10-04 IST. Application runtime checkpoint: `85ddb79`; build/runner hardening: `b869f6d`.
Saved reports identify the exact source checkpoint used.
M1 (`0fd2104`) was merged into main (`2c4f3db`), which already contained M2,
M3 and M4. Integration commits unify security, connect the frontend, and execute
measured lab jobs. No secondary M2 branch was merged.

## Resulting application

- One sync SQLAlchemy/psycopg persistence system and Alembic head `e4f200000001`.
  P2 authentication now uses P1's transactions, UUID models and shared v1 DTOs.
  `uv.lock` is authoritative; `requirements.txt` is its generated production export.
- Real visitor email/password registration and login, invitation login, durable
  opaque `fd_session` cookies, strict Origin and
  CSRF checks, privilege allowlists, owner checks, credential revocation, and
  atomic Redis account/session/credential/network/global limits. Self-registration
  creates participant identities only and never grants drop eligibility. Logout
  clears the actual returned cookie.
- Complete drop, eligibility, idempotency, receipt, draw, reservation, expiry,
  promotion, inventory and public proof routes. Frozen membership and ranking
  remain immutable. The independent verifier reproduces the lottery ordering.
- Real typed frontend: discovery, visitor registration, email/invitation sign-in,
  sign-out, invitation check, saved entry,
  offer countdown, confirmation, receipts, proof download, organizer create/edit,
  grants/revocation, publication/cancellation, metrics/audit/CSV, profile and lab.
  Mock fixtures and fabricated lab counters were removed.
- PostgreSQL-authoritative lab jobs, one active job across replicas, owner-scoped
  reports/exports, dedicated bounded k6 runner, fresh matched identities/drops
  per trial, real HTTP operations, and DB/proof reconciliation. Stops retain
  artifacts; interrupted generator jobs are failed explicitly on worker restart.
  Policy comparison reports policies separately. Trial bootstrap intervals use
  independent trial outcomes; one trial reports no confidence interval.
- Runtime/frontend Dockerfiles and Compose wiring are present. The gateway is
  the sole trusted proxy. Uvicorn leaves peer addresses intact for IP validation.
  PostgreSQL 18's volume mount uses `/var/lib/postgresql`; private lab fixtures
  live in a separate restricted runner-only volume. The runner has a 1 GiB /
  2 CPU budget; identity records and cohort indexes use k6 SharedArray storage. Normal profile disables lab/FCFS.

## Executed checks

| Check | Result |
| --- | --- |
| Backend pytest against PostgreSQL 18.6 UTF-8 and Redis 8.2.1 | **97 passed**, plus 4 unittest subtests |
| Backend Ruff lint and formatting | Passed |
| Fresh migration / metadata comparison | Passed; one head, no drift |
| M2 legacy migration with an existing inactive user, credential and session | Identity/digest/label preserved; session archived and requires re-login |
| Legacy downgrade to P2 revision and re-upgrade | Passed |
| Already-stamped M1 database clone downgrade/re-upgrade | Passed |
| Shared contract export and both generated TS outputs | Passed; 33 paths |
| Frontend TypeScript production build and lint | Passed |
| Production dependency audit | 0 vulnerabilities |
| Browser organizer flow | Login, draft creation, real grant, publication, live inventory and lab report passed |
| Browser participant flow | Login, eligibility, entry, offer, confirmation, receipt and refresh passed |
| Independent lottery proof verification | Passed, including real authenticated integration journey |
| Two independent socket API processes | Shared 30-read budget: exactly 30 allowed / 10 rate-limited across two sessions |
| Actual Redis shutdown/restart | Readiness degraded; session read 200, protected write 503; same-key profile retry recovered with 200 |
| Actual k6 normal run | Completed; HTTP and DB results reconciled; no oversell/duplicate owner/5xx/network error |
| Actual matched FCFS/lottery run | Completed; both policy inventory audits passed |
| Actual two independent k6 trials | Completed; 8 provisioned identities; measured trial bootstrap intervals |
| Actual running-job stop | STOPPED; partial generator artifacts retained |
| SIGKILL of isolated lab worker and replacement worker startup | FAILED / LAB_RUN_INTERRUPTED; partial artifacts retained |
| Normal and demo Compose configuration | Validated with Docker Compose 2.39.4 |
| Dockerfile base image references | Registry manifests verified for Python 3.12.14, uv 0.12.22 and k6 1.3.0 |
| Production-only locked environment | Fresh frozen install imports all API paths |
| Private environment initializer | Refuses incomplete normal origin; mode 0600; preserves existing file |

Core tests keep their clearly labelled test-only security adapter for deterministic
allocation races. Security and integration tests exercise real authentication,
CSRF and Redis with no bypass. The additional socket and browser checks exercise
separate running processes. Core coverage includes concurrent entry/confirmation,
row-lock deadline boundaries, sealed snapshots, and allocation worker SIGKILL
recovery. Test fixtures refuse non-test-profile databases and require `_test`
PostgreSQL names plus Redis database 1 or 15.

## Evidence and practical limits

- [Measured normal smoke](reports/integration-smoke.json),
  [matched policies](reports/integration-policy-comparison.json),
  [two trials](reports/integration-two-trials.json), and
  [replica/outage evidence](reports/integration-replicas.json).
- [Refreshed confirmed browser receipt](reports/browser-confirmation.png).
- These are small real smoke workloads. No 50,000-identity benchmark, sustained
  production capacity, or universal fairness conclusion is claimed. Lottery
  fairness is conditional on the admitted, frozen pool and identity provisioning.
- CPU/memory/connection/inflight generator peaks are uninstrumented and null.
  Offer outcomes are observed after initial allocation; subsequent confirmation
  and expiry can change live inventory. Target RPS is calibrated to healthy
  iteration request counts; short schedules, failures and retries change achieved RPS.
- Shared-IP topology and host-controlled Redis/worker disruption scenarios remain
  explicit manual experiments using `scripts/failure_injection.ps1`; the API
  rejects unattended requests for those three scenarios.
- Docker's daemon is unavailable in this environment. Container image builds and
  full Compose startup were **not executed**. Equivalent application processes,
  workers, database, Redis, k6 and browser paths were run locally. Deployment
  requires the documented Docker preflight on a host with a running daemon.
- The existing Tailwind 3 development toolchain reports 5 high-severity transitive
  `braces` findings. `npm audit fix` has no compatible repair; its proposed fix
  requires a Tailwind 4 migration. Production dependency audit reports 0 findings.
- Two upstream test-client cookie/deprecation warnings remain. No human review,
  production deployment, or team signoff is claimed.

The P2 archive schema deliberately preserves historical fields and unbound
sessions/grants for review. Migration refuses legacy values that violate the
shared constraints instead of silently truncating identities. Restore/migrate
in a disposable clone before applying to an existing deployment.
