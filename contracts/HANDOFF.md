# M1 shared bootstrap / wire contract v1.0

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

The API process command is imported/smoked with TestClient at bootstrap; socket
startup is verified during the final M1 checkpoint. Configuration export does not
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
