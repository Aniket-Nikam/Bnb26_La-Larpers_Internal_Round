# FairDrop integrated workspace

This branch combines the latest P3 frontend from `origin/main`, the runnable P2
security backend from `origin/M2`, and the P4 infrastructure/attack-lab work from
`origin/codex/m4-infra-lab`.

The merge is source-clean and its independently runnable pieces are verified.
It is not yet a complete FairDrop application because the P1 drop, inventory,
allocation worker, and OpenAPI contract have not been supplied. The frontend is
still backed by explicitly labelled development fixtures.

See [INTEGRATION_REPORT.md](INTEGRATION_REPORT.md) for exact source revisions,
verification results, and remaining blockers.

## Verified commands

From the repository root:

```powershell
# P4 unit tests
backend\.venv\Scripts\python.exe -m pytest backend\tests\lab -q -p no:cacheprovider

# Collect all P2/P4 tests
backend\.venv\Scripts\python.exe -m pytest backend\tests --collect-only -q -p no:cacheprovider

# Frontend
Set-Location frontend
npm ci
npm run lint
npm run build
npm audit --omit=dev
```

The complete P2 integration suite additionally needs isolated PostgreSQL and
Redis instances. Full Compose startup remains blocked until the P1-owned worker,
Dockerfiles, and API contract listed by `scripts/preflight.ps1` are present.

## Current service surface

The backend currently mounts:

- `POST /api/v1/auth/session`
- `GET /api/v1/auth/me`
- `DELETE /api/v1/auth/session`
- `PATCH /api/v1/profile`
- `GET /api/health/live`
- `GET /api/health/ready`

Drop entry, allocation, organizer drop management, and admin lab HTTP routes are
not mounted yet because their P1 interfaces are absent.

## P4 operational assets

- `compose.yaml` and `infra/compose.demo.yaml`
- bounded lab runner and metric aggregation under `backend/app/lab/`
- load scenarios under `tests/performance/scenarios/`
- preflight, failure-injection, reset, and demo-runbook scripts under `scripts/`

Do not claim benchmark or fairness results until the authoritative allocation
path is integrated and the scenarios have been run against it.
