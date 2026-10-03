# FairDrop implementation memory

Current phase: M1/M2/M3/M4 integrated on `main`. User explicitly authorized merging
M1 into main and integrating the merged team implementations. The earlier
instruction to push only M1 is superseded for this integration request.

Main originally: `2c4f3db` (already contained M2, M3 and M4).
M1 delivered branch: `0fd2104`. Integration runtime checkpoint: `85ddb79`; build/runner hardening: `b869f6d`.
Separate commits cover merge/security, frontend, migration compatibility, and
measured lab/runtime integration. No alternate M2 branch was merged.

One ORM, psycopg/uv dependency stack, migration head `d3f100000001`, shared DTOs,
31 v1 API paths and generated frontend types. Sessions use `fd_session`; role,
Origin/CSRF, revocation and Redis limits are active across the domain routes.
M2 historical tables remain archived; identities and credential digests migrate,
unbound old sessions require re-login. M1 allocations retain immutable manifests,
rankings and durable worker recovery. Frontend fixtures were removed.

Lab jobs use shared LabRun rows and a separate isolated worker. Fresh synthetic
accounts/grants/drops are provisioned per independent trial. k6 uses ordinary HTTP
routes; reports reconcile database outcomes, proof and measured HTTP samples.
Stopped/interrupted runs retain partial artifacts and are never marked complete.
Normal profile disables lab/FCFS; host-controlled outage/topology scenarios are
manual and rejected by the unattended lab API.

Verification: 93 backend tests + 4 subtests; real PostgreSQL 18.6 and Redis 8.2.1;
fresh, M2-legacy and M1-upgrade/downgrade checks; no metadata drift; frontend build,
lint and 0 production dependency vulnerabilities. Real two-process quota,
Redis shutdown/recovery, k6 normal/policy/two-trial/stop/crash checks and browser
organizer/participant/confirmed receipt refresh passed.

Docker configuration and base manifests were checked, but the local Docker
daemon is unavailable, so image builds/full Compose startup are unverified.
Tailwind 3 retains 5 development-only transitive audit findings; a major Tailwind
migration is required for the suggested fix. No production deployment, scale
benchmark or human review is claimed. Details: INTEGRATION_REPORT.md.

Canonical specifications remain in docs/. Existing TypeScript ingress experiments
are preserved outside the default runtime. Runtime artifacts and synthetic secret
fixtures used for tests stayed under /tmp; public aggregate evidence is in reports/.
