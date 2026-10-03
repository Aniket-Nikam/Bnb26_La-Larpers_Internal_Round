# Member 4 progress

- Updated UTC: 2026-10-03T16:29:58Z
- Branch: `codex/m4-infra-lab`
- Base commit: `7eedd2f`
- Scope: infrastructure, isolated attack lab, metrics, performance/E2E ownership,
  operational scripts, reports, and final integration.
- Current phase: pre-bootstrap P4 foundation; shared bootstrap handoff NOT DONE.

## Implemented on this branch

- Strict allowlisted run contract with specification caps and rejection of
  browser-supplied target/script/command/seed fields.
- Atomic on-disk subprocess status/artifact store; one active run; QUEUED,
  RUNNING, STOPPING, STOPPED, COMPLETED, FAILED transitions; bounded timeouts;
  safe error messages; `shell=False` argument-array execution; partial retention.
- Separate execution/artifacts for every requested trial. Cross-trial percentiles
  are not fabricated from already-aggregated percentile values.
- PRD metric aggregation per unique accepted identity, actor versus credential
  counts, bot advantage null reasons, latency quartile/Jain/correlation validity,
  Wilson 95% intervals, and non-finite JSON rejection.
- k6 cookie/session/CSRF scenarios for normal, early bot, retry flood, credential
  farm, shared IP, reconnect, worker restart, Redis failure, expiry race, and
  policy comparison. Traffic goes through normal API routes.
- Normal/demo Compose separation, persistent PostgreSQL, Redis, two API replicas,
  worker, static frontend build, one-origin Nginx, fixed trusted proxy address,
  bounded pools, startup dependencies, health checks, graceful stop periods, and
  isolated runner profile.
- Explicit demo-only reset and worker/Redis failure-injection scripts.
- Operational status README, private-fixture guidance, report directory policy,
  E2E dependency checkpoint, and five-minute demo runbook.

## Actual checks

| Command/check | Result |
| --- | --- |
| `python -m unittest discover -s backend/tests/lab -p "test_*.py" -v` | PASS, 14 tests |
| `python -m compileall -q backend/app/lab backend/tests/lab` | PASS |
| `node --check` for all performance scenario JavaScript files | PASS |
| Normal `docker compose config --format json` | PASS; 8 services; all four restricted flags `false` |
| Demo override with `--profile lab` | PASS; runner present; lab/FCFS/seed true, development mocks false |
| `git diff --check` | PASS |
| Real k6 HTTP run | NOT RUN; k6 absent and integrated API/provisioner missing |
| Full Compose build/start | NOT RUN; teammate-owned Dockerfiles/entrypoints missing |
| Playwright browser suite | NOT RUN; frontend and accessible locators missing |

Environment observed: Windows PowerShell, Python 3.13.14, Node 24.13.0,
npm 11.6.2, Docker 29.5.3, Docker Compose 5.1.4. `k6` and `make` unavailable.

## Blockers and owner handoffs

- P1: provide shared LabRun ORM/repository integration, backend dependency lock,
  FastAPI mount, migrations, worker, authoritative outcomes/inventory query,
  FCFS_DEMO, OpenAPI examples, and backend Dockerfile targets `runtime` and
  `lab-runner`. Until then `/api/v1/admin/lab` is not mounted and reports are
  explicitly partial.
- P2: provide `require_organizer`, CSRF/Origin/idempotency integration, private
  credential provisioner, shared limiter thresholds, and tested Redis behavior.
- P3: provide frontend Dockerfile build target/output `/app/dist` plus stable
  Playwright locators and real lab UI.
- P4 next: integrate the router against P1/P2 exact imports; add DB reconciliation;
  install/execute k6 smoke; implement real Playwright journeys; then run measured
  smoke, 1k, 10k, and only attempt 50k if delivery/headroom supports it.

`docs/memory.md` remains the original inactive template. P4 has not claimed
central-writer ownership before the required P1 bootstrap handoff. Human review
and whiteboard sign-off remain PENDING.
