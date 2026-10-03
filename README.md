# FairDrop

M1, M2, M3 and M4 are integrated on `main`: a FastAPI/PostgreSQL allocation
backend, durable invitation sessions and shared Redis limits, a React frontend,
and an isolated measured attack lab. All 33 v1 route paths use one shared schema.
The frontend uses real API responses; development fixtures were removed.

## Demo deployment

Requires Python, Docker with Compose, and a running Docker daemon. From the root:

```sh
python3 scripts/init_env.py --demo
# Refresh APP_COMMIT in .env after updating the checkout.
python3 scripts/preflight.py --demo
make demo-up
```

Open `http://localhost:8080`. The demo uses its own `fairdrop-demo` Compose project
and volumes. Keep its database separate from normal deployments. The stack has
PostgreSQL 18, Redis, two API replicas, an allocation worker, a dedicated k6 job
worker, migrations, and a same-origin gateway serving the built frontend.

Provision an organizer offline, then use its code on the invitation tab of the
sign-in page. Provisioning prints each raw code once; retain it privately:

```sh
docker compose -p fairdrop-demo --env-file .env -f compose.yaml -f infra/compose.demo.yaml exec api-a python -m app.security.provision --name Organizer --role organizer
```

Visitors can register with email/password or sign in with an invitation
credential. Registration creates a participant account and signs it in, but does
not grant access to any drop. Each participant's profile shows the public account
ID an organizer uses to grant invitations.
Create a draft, grant invitations, and publish it before its scheduled entry
start. The allocation worker opens/closes the window, freezes membership,
publishes the ranking, offers seats, and promotes expired offers. A saved receipt
survives refresh; participants confirm their own offers before the server deadline.
Download a public proof and independently verify it:

```sh
cd backend
uv run python -m app.audit.verifier /path/to/proof.json
```

The lab provisions fresh synthetic accounts, credentials, grants and drops for
each trial. It uses ordinary HTTP entry/confirmation routes and the ordinary
allocation worker. Reports reconcile attempts, unique accepted identities,
initial offers, inventory, and proof verification against PostgreSQL. Policy
comparison keeps FCFS and lottery outcomes separate. Raw credentials stay in a
private runner volume; exports contain no credentials or session secrets.

Normal, early-bot, retry-flood, credential-farm, reconnect, expiry-race and policy
comparison runs are available in the demo UI. Shared-IP topology, worker restart
and Redis failure experiments require the documented host-side controller and
manual k6 invocation; the API rejects unattended requests for those experiments.
Runs are capped by configured limits and a conservative 250,000 planned-request
budget. Stops retain partial artifacts; a killed job worker marks interrupted
experiments failed on restart. It never relabels incomplete data as completed.

## Normal deployment

```sh
python3 scripts/init_env.py --origin https://your-host
python3 scripts/preflight.py
make up
```

Provide TLS termination for the configured public origin. Normal profile requires
HTTPS, Secure cookies and stable random digest/encryption keys. It disables the
lab and FCFS comparison. Offline organizer/admin provisioning requires the
explicit `--production` CLI option. Redis failure preserves authenticated reads
and durable sessions while protected writes return retryable 503 responses.

## Local development and verification

Backend commands run from `backend/`; configure PostgreSQL/Redis and stable keys
in the environment. `PUBLIC_ORIGIN` must match the browser origin exactly. For
Vite development use `http://127.0.0.1:5173` with demo profile and `COOKIE_SECURE=false`.
Vite forwards `/api` to the backend on port 8000.

```sh
cd backend
uv sync --frozen --python 3.12
uv run alembic upgrade head
uv run alembic check
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers
# Separate terminal with the same environment:
uv run python -m app.allocation.worker
# Optional demo lab worker; set LAB_ENABLED, LAB_TARGET_ORIGIN,
# LAB_SCRIPT_ROOT, private/artifact roots and install k6 1.3.0:
uv run python -m app.lab.worker
```

```sh
cd frontend
npm ci
npm run dev
npm run lint
npm run build
```

Tests require a migrated disposable database ending `_test`, `APP_PROFILE=test`,
and a disposable Redis database 1 or 15. Security/integration fixtures truncate
test data and flush that Redis database. They refuse other profiles/database names.

```sh
cd backend
uv run ruff check app tests
uv run ruff format --check app tests alembic
uv run pytest -q
# Export the source contract, then regenerate both TS outputs:
APP_PROFILE=test uv run python -m app.core.export_contract
cd ../contracts
npm ci --ignore-scripts
npm run generate
npm run generate:frontend
```

See [INTEGRATION_REPORT.md](INTEGRATION_REPORT.md) for executed checks and limits,
[contracts/HANDOFF.md](contracts/HANDOFF.md) for the shared interfaces, and
[docs/hackathon-demo.md](docs/hackathon-demo.md) for the five-minute judge flow.
