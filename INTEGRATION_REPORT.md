# P2 + P3 + P4 integration report

Date: 2026-10-03

## Integrated sources

| Area | Source | Revision |
| --- | --- | --- |
| P3 frontend | `origin/main` | `31fbb41` |
| P2 security backend | `origin/M2` | `7f62464` |
| P4 infrastructure and attack lab | `origin/codex/m4-infra-lab` | `f2bde41` |
| Integration branch | `codex/integration` | merge commits `5b1705d`, `49f3c08` |

`origin/codex/m2-security` was not layered on top of `origin/M2`. It is an
earlier, protocol-based alternative that replaces the same security modules and
does not contain the FastAPI entrypoint, SQLAlchemy models, migrations, or locked
backend requirements provided by `origin/M2`.

## Verification results

| Check | Result |
| --- | --- |
| Merge conflicts | Resolved; only `.gitignore` required a manual union |
| P4 lab unit tests | PASS: 14/14 |
| P2/P4 pytest collection | PASS: 60 tests collected |
| Python bytecode compilation | PASS |
| Python dependency consistency | PASS: `pip check` found no broken requirements |
| Backend liveness | PASS: `/api/health/live` returned 200/alive |
| Backend dependency degradation | PASS: readiness reported PostgreSQL and Redis unavailable without a 500 |
| Frontend lint | PASS |
| Frontend production build | PASS: 2,932 modules transformed |
| Production npm audit | PASS: 0 known production vulnerabilities |
| Compose normal profile parse | PASS |
| Compose demo profile parse | PASS |
| Performance-scenario JavaScript syntax | PASS |
| Full P2 database/Redis suite | NOT RUN: isolated services unavailable |
| Real k6 traffic | NOT RUN: k6 is not installed and allocation routes are absent |
| Full Compose build/start | BLOCKED by missing P1/packaging files listed below |

The full npm development-tree audit still reports five high-severity findings
through Tailwind CSS 3 build tooling. npm's offered fix is a Tailwind 4 major
upgrade. These packages are build-only and are not present in the production
dependency audit, but the toolchain upgrade should be scheduled and regression
tested.

The production build also warns that its main JavaScript chunk is about 768 kB
(234 kB gzip), above Vite's 500 kB advisory threshold. Route-level code splitting
is recommended before treating frontend performance as finalized.

## Integration fixes applied

- Updated `asyncpg` and `psycopg2-binary` pins to releases supporting Python
  3.13 on this host.
- Added the repository root to pytest's import path and fixed the async fixture
  loop-scope warning.
- Fixed React type-only imports and removed an unused icon import.
- Moved shared development fixtures out of a React component module so lint is
  clean.
- Classified Tailwind, PostCSS, and Autoprefixer as development dependencies;
  the production npm audit is now clean.

## Remaining blockers

`scripts/preflight.ps1 -RequireLoadTools` correctly reports:

- `backend/Dockerfile`
- `backend/app/allocation/worker.py`
- `frontend/Dockerfile`
- `contracts/openapi.json`
- local `k6` executable

More importantly, the merged backend has no drop, entry, inventory, or
allocation routes. The frontend still uses `DEV_FIXTURES`, and the P4 lab runner
is not mounted under an admin HTTP router. Those are P1 integration dependencies,
not merge conflicts.

## Verdict

P2, P3, and P4 coexist cleanly and their available isolated checks pass. The
combined repository is not yet end-to-end complete or suitable for fairness/load
claims until P1 lands and the blocked integration suites are executed.
