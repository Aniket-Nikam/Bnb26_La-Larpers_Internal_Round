# FairDrop — AI and Engineering Rules

Build pack: FairDrop merged specification v1.0 · 2026-10-03.
Status: specification only; no code, benchmark, completed phase or human review is claimed.

## 1. Authority and session start
Follow explicit user instructions first. Within the project, architecture.md settles normative API details; generated OpenAPI must match that specification; prd.md settles scope; architecture.md settles business/system design; design.md settles visual rules; phases.md settles dependency order; this file settles workflow. If two documents disagree, record the concrete conflict and resolve it with the relevant owner rather than implementing both interpretations.

Read this file, prd.md and your assigned member prompt in phases.md at every new coding session. Read memory.md if it exists, then your own progress/person-N.md and current contracts. Inspect relevant implementation files before editing. Do not reread the entire repository by default; use targeted search. Verify claimed progress against files/commits/check results.

These are customer-facing product rules even though a hackathon profile uses mock payment and seeded actors. Fast isolated experiments may be rough; their code/results cannot become customer-facing defaults without integration review and understanding.

## 2. Boundaries and file ownership
Use architecture.md's ownership map. Four people build one application. The bootstrap owner may create skeleton files before the checkpoint. Afterward no parallel editing of another person's files, root contracts or shared migrations without a handoff. Owner fixes ordinary cross-area findings.

Only P1 edits shared models, migrations, backend dependencies/main wiring and contracts. P2 implements security using those models. P3 owns the entire frontend/design token system and frontend dependencies. P4 owns lab/infra/tests/reports and the central integrated memory after bootstrap.

Review systems are read-only unless assigned a concrete owner-approved patch. Do not spawn additional coding agents by default. Never switch stacks, duplicate authentication, start a second app, install an unrelated framework, delete work or rewrite a teammate's module without a concrete reason and handoff.

## 3. Dependencies
Approved baseline:
- React, TypeScript, Vite, React Router, TanStack Query.
- Tailwind and Radix primitives; Lucide; Recharts for measured charts.
- React Hook Form/Zod for client forms; Pydantic remains server authority.
- FastAPI/Pydantic, SQLAlchemy/Alembic, psycopg, redis-py.
- cryptography for authenticated seed-at-rest encryption only; no custom cipher.
- Standard hashlib/hmac/secrets for commitments and randomness.
- pytest/httpx, Playwright, k6.
- Docker Compose/Nginx; formatting/linting tools that match these languages.
Verify compatible releases at bootstrap, pin exact resolved versions/locks, and avoid introducing multiple tools for the same responsibility. Use migrations, not startup create_all in production.

Not in the baseline: Firebase/Supabase/Auth0 replacement databases/auth, Next.js replacement app, Celery/Kafka/Kubernetes, blockchains, LLM calls in request processing, browser fingerprint databases, proprietary CAPTCHA/payment requirements, arbitrary hosted analytics.

Scrapling is optional research tooling, not a required runtime dependency. If later used, isolate it in tools/research with a separate pinned environment and bounded permitted-page extraction. It does not replace k6, auth or bot handling. Do not add crawling, proxy rotation or anti-bot bypass as a FairDrop product feature merely because the library supports them. This tooling is outside the required runtime and submission scope.

Do not invent a package API; check installed versions/official docs when uncertain. Surface a real dependency blocker rather than generating guessed integration code.

## 4. Core invariants
- One entry per eligible identity/drop.
- One current owner per slot; no more than configured slots.
- One active/confirmed reservation per identity/drop.
- Fixed frozen participant manifest and fixed persisted ranking.
- No extra chances for retries, request volume, network speed or multiple devices.
- No default suspicion-weighted or network-weighted draw.
- Protected atomic close/entry and confirm/expire transitions.
- Fresh authoritative clock at deadline checks.
- Valid confirmation can happen only once for an active owned offer.
- Acknowledged state is durable before success.
- Audit and operation state stay transactionally aligned.
Do not replace DB invariants with frontend checks, Python in-memory dictionaries, Redis-only locks/counters or check-then-write logic.

## 5. Errors and retries
Use architecture.md (Shared API contract)'s single error envelope and stable codes. Safe messages, request ID and retryable flag. No stack traces, SQL text, invitation values or raw request cookies in browser/log output.
401 SESSION_REQUIRED -> recover session/re-authenticate.
403 FORBIDDEN or CSRF_REJECTED -> deny and explain.
409 ENTRY_CLOSED, OFFER_EXPIRED, INVALID_STATE, IDEMPOTENCY_CONFLICT -> reconcile state.
422 VALIDATION_ERROR -> field guidance.
429 RATE_LIMITED -> bounded backoff; do not erase accepted state.
503 TEMPORARILY_UNAVAILABLE -> retryable service condition; no claimed successful write.
500 INTERNAL_ERROR -> genuine unexpected fault with request ID.
501 NOT_IMPLEMENTED -> honest development stub only; required routes must not remain stubs in the completed demo.
Do not turn every exception into a 200 result. Do not count expected 4xx as application crashes. Centralize exception mapping and sanitization.

Bound retries with jitter, overall deadlines and idempotency. Frontend uncertainty requires GET reconciliation. A fresh idempotency key for each click must not bypass domain uniqueness. Never retry money-like operations without a durable operation model.

## 6. Authentication/privacy
Use durable opaque cookie sessions and server authorization for roles and object ownership. Enforce CSRF and Origin on browser writes. API clients/test runners follow the same normal auth model. Trust only configured proxy hops.

Credentials grant access; eligibility grants allow per-drop entry. Do not label IP/email/invitation control as proof of humanity. Do not deny all campus users because they share an address. Server-facing risk signals do not secretly change published lottery rules.

Store credential/token digests; keep signing/digest/seed-protection keys in environment/secret configuration, not Git. Seed fixture credentials exist only in isolated demo setup and must not be logged by services. Do not return arbitrary credential lists from public routes.

Escape rendered data, use parameterized ORM/SQL, cap input size and paginate. Public receipts/manifests contain random pseudonyms only. Profile payloads cannot modify role, eligibility, owner IDs or seat status.

## 7. Lab and experimental isolation
Only organizer-authenticated demo environments can start load jobs. Targets come from configuration, never request URLs. Scenario names are allowlisted; numeric parameters have caps; subprocesses use argument arrays and limited resources. Provide stop/timeout behaviour and audit lab actions. No third-party/public targets.

Ground-truth human/bot labels live in the harness, not production detector inputs. Shared-IP tests require controlled proxy/network topology, not trusting arbitrary forwarded headers. Report simulated actors accurately; do not claim the harness established actual human intent.

Historical weighted policies and proof-of-work may be compared as isolated experiments. They are not the production default. No changes to election probabilities simply to improve the bot-share chart.

## 8. Frontend honesty and seamless recovery
One token/component system, one typed API client. No production mock fallback, local fake winners, random metric generators or fabricated activity. Demo data is explicitly seeded; measured data is visibly labelled by run/time.

Disable double submission for usability but rely on backend uniqueness. Server state determines accepted/confirmed/expired status. A clock reaching zero prompts refetch, not an invented transition. Preserve receipt and selection state across routes/reconnects. Poll conditionally and include that traffic in tests.

Avoid queue position before draw publication. Explain expiry, waitlist and cancellation clearly. Respect keyboard access, focus, contrast and reduced motion.

## 9. Verification and claims
Run appropriate meaningful tests from phases.md. Use real PostgreSQL for concurrency evidence. Record commands, environment and actual results. "Pass" means executed successfully, not expected to pass. Document a blocker and its scope if a check cannot run.

Never extrapolate the attached small simulation to 50k live concurrency. Measure delivered workload, generator limits and hardware. Interpret randomized comparisons with repeats/intervals; 0 observed bot wins is not a universal zero-risk guarantee. Source summary's integrity claims remain supplied until independently reproduced.

Whiteboard decisions are proposed until humans understand the implemented path and attach evidence. No AI may mark a human review completed on their behalf.

## 10. memory.md protocol — create only after coding starts
Do not create memory.md for this documentation package. P1 copies memory.template.md to memory.md when the first implementation edit begins and replaces placeholders with observed facts. P1 owns it until the bootstrap handoff; P4 then becomes the sole central writer. Teammates maintain their own progress/person-N.md to avoid merge collisions. No progress files are fabricated before work starts.

Required central sections:
- Updated UTC time, integration branch and known commit.
- Current phase; completed phase gates with evidence.
- Table per person: branch/head, active task, current files, completed files, remaining work.
- Last verified commands/results/environment; failed or not-run checks.
- API/schema/dependency versions and unresolved contract changes.
- Blockers, owner and next concrete action.
- Implemented decisions linked to whiteboard.md IDs.
- Short next-session instructions.
Never store secrets or all terminal logs. Do not mark an entire file complete just because it exists; specify behaviour implemented and checks run. Stale branch data is visibly stale. Completion entries reference a commit/test result, not confidence.

Each teammate's progress record uses: timestamp, branch/commit, scope, in-progress files, implemented behaviours, actual checks, blockers, next steps and cross-owner handoffs. Update at a useful checkpoint, before switching tools/chats, and before handing off. New sessions validate against current code.

## 11. Human defence
Each customer-facing feature has an accountable person. Update whiteboard.md when implemented design changes; describe why, alternatives, malicious actor behaviour, failure modes, data structures and evidence. Proposed answers are rehearsal material, not proof of understanding. Before customer-facing release a human explains the implemented system and records their review; no line-level memorization required.


## 12. Concrete AI task and handoff rules

At the start of implementation, state your member number, current phase, owned paths and dependency checkpoint. Then inspect the relevant code, implement the assigned behavior, run appropriate checks, and hand off exact changed paths/results. Do not end at a proposal when implementation is authorized. Do not request repeated confirmation for routine reversible work within your assigned scope.

For any cross-owner change, send: problem, affected route/schema/files, proposed patch or contract example, required evidence and owner. The owner applies it or explicitly hands off exclusive edit ownership. A handoff must have a named recipient and endpoint; a general permission to review is not permission to rewrite. P1 integrates shared schema/OpenAPI changes, P3 regenerates frontend types, and P4 validates integration before memory marks them merged.

Before changing database/security/allocation policy, check the associated whiteboard decision and write a short reason. Do not silently relax a constraint because a test fails. Never mark test fixtures or empty stubs as implemented behavior.

Use one package manager and committed frontend lockfile; pin Python dependencies in a reproducible lock/constraints workflow chosen at bootstrap. Additional libraries require a concrete need and owner-coordinated decision. Keep handlers typed with explicit Pydantic response/error models. Do not enable extra frameworks, LLM inference, PoW, fingerprinting or a different auth system merely because an AI recommends them.

Each mutation's timeout handling is explicit: preserve the operation key, reconcile GET state, then retry boundedly with jitter if still unresolved. Honor Retry-After. Default automated browser retry cap is three attempts and a 30-second overall budget; after that offer a manual recovery action. Login credentials and CSRF tokens stay out of persistent browser storage. A nonsecret pending operation key may be retained per tab; refresh recovery relies on server state, not it.

Do not spend the final hours implementing optional features while correctness or integration gates are red. If resources/time block load targets, preserve integrity tests and measured small runs, document the limit, and ship an honest demo. Customer-facing release understanding remains a human responsibility; isolated experiments can prioritize speed without pretending they passed that review.
