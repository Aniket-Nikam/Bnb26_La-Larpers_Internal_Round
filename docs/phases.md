# FairDrop — implementation phases

Build pack: FairDrop merged specification v1.0 · 2026-10-03.
Status: specification only; no code, benchmark, completed phase or human review is claimed.
Current status: specification only. No phase is claimed complete.
Progress moves into memory.md only when actual coding begins.

## Dependency order
| Phase | Deliverable | Main owner | Gate |
| --- | --- | --- | --- |
| 0 | Shared skeleton/contracts | P1 with P4 run setup | All teammates consume one checkpoint |
| 1 | Login/session/eligibility and public shell | P2 + P1 + P3 | Real browser login and authorized drop read |
| 2 | Unique durable entry and receipt | P1 + P3 | Retry/reconnect/concurrency recovery |
| 3 | Close, draw and confirmation slice | P1 + P3 | End-to-end real offered/confirmed ticket |
| 4 | Expiry, promotion and restart recovery | P1 + P2 + P4 | Race/restart tests on real DB |
| 5 | Complete website and organizer workflows | P3 + P1/P2 | All required screens use real API |
| 6 | Attack laboratory and comparison | P4 + P1/P2/P3 | Bounded real HTTP scenarios/reports |
| 7 | Capacity evidence and integration | P4 + all owners | Measured workload and fresh-checkout run |
| 8 | Whiteboard/demo/release review | Humans + all owners | Explain decisions and demonstrate evidence |

Parallel preparation is allowed; dependent stateful work waits for the corresponding contract/gate. Do not try to generate the entire app in one uncontrolled pass.

## Phase 0 — foundation
P1 inspects the repository and preserves existing code. Establish a single stack/lock strategy, folder ownership, shared ORM models including auth/eligibility/idempotency, error mapping and security/lab interfaces. Expand architecture.md (Shared API contract) into complete exported OpenAPI schemas and representative examples, including lab report types. Publish an API contract version and frontend generation command.

Mount stub routers with explicit not-implemented behaviour and deny-by-default security. Never return a fake successful write. Health distinguishes liveness/readiness/capability. Include separate modes for normal app, isolated demo and tests.

P4 establishes Compose skeleton with persistent PostgreSQL/Redis, same-origin proxy, services/env names and worker entrypoint placeholder. P1 may provide a minimal temporary bootstrap run path if P4 has not started, then hands ownership over.

Create memory.md only once implementation starts. P1 records actual bootstrap edits/checks and transfers central writing to P4 at the checkpoint. Commit the shared foundation; all teammates clone/rebase from its hash.

Gate: install/run documented; schemas export/type generation works; models migrate; stubs are honest; hooks/ownership are written; no competing apps or auth.

## Phase 1 — authentication and public structure
P2 implements invitation credentials, durable session, CSRF, owner/role authorization, profile and per-drop grants using shared models. Seed utilities support an organizer and participants in demo-only mode.

P3 builds app shell, discovery/details, sign-in and route guards; P1 provides real public detail/list and drop ownership. Backend authorization is independent of UI guard.

Gate: real browser sign-in, session fetch, logout and return-to flow; refreshed session survives API restart; cross-owner/non-organizer requests denied; no secret browser storage; eligible/not-eligible states distinguishable.

## Phase 2 — durable entry
Implement coordinated entry transaction, scoped idempotency, unique per-drop user entry, random public receipt ID and persisted history. Display accepted status only after commit; /me reconciles lost responses. Begin same-account multiple-tab tests and real backend rate limits.

Gate: same and different idempotency keys under concurrency still yield one entry; same identity across devices has one entry; eligible shared-IP identities each enter; timeout after commit recovers receipt; late admission denied by DB deadline.

## Phase 3 — first complete user journey
Implement publication/closure, frozen snapshot, commitment/ranking and first offers. Implement confirmation with row locking and fresh clock checks. P3 consumes these states directly.

Gate: login -> eligible entry -> close -> draw -> offer -> confirm -> ticket -> refresh uses only real API. Duplicate draw calls reuse the same run. Proof bundle reproduces ranking; no private identity leaks.

Do this before completing all organizer charts or optional visual polish.

## Phase 4 — integrity under failure
Add expiry, promotion cursor, deterministic resumption, worker reconciliation and graceful API/worker shutdown. Integrate rate limiting across replicas and degraded Redis handling.

Gate: capacity/identity uniqueness under concurrent initial offers; confirm/expire at boundary produces one valid result; close/insert race respects snapshot; worker kill/restart does not reseed/reorder/duplicate; session Redis outage leaves durable identities/entries intact. Record admissions/confirmation lost to unavailable service honestly.

## Phase 5 — complete website
Finish discovery filters/pagination, profile/history, receipt/ticket layouts, verifier, organizer drafts/scheduling/publication/cancellation/content editing, integrity/audit monitor, forbidden/not-found states and mobile navigation. Cancel only eligible pre-allocation phases and propagate participant cancellation.

All fields/buttons correspond to committed endpoints. Treat prototype adapters as development-only and remove them from production. Accessibility and offline/throttling UI are required.

Gate: screenshot/interaction review at 360px/tablet/desktop; keyboard path; all visible controls work; organizer sees only owned data; history/settings persist; no manufactured metrics or hidden mock routes.

## Phase 6 — adversarial laboratory
P4 implements allowlisted runner with caps/cancel/status/report files. P1 completes demo-only safe FCFS mode using the same invariants; P2 keeps identity/limit policy identical across controlled comparisons; P3 wires live lab screens.

Scenarios: normal, early bot, duplicate/retry flood, multi-credential farm, shared IP, reconnect/lost response, worker restart and expiry boundary. Test harness cohorts never feed allocation. Retain source summary as historical imported report clearly labelled supplied/unreproduced.

Gate: start/stop and failed-run states function; real HTTP traffic; report agrees with DB counts; matched comparator; no arbitrary target or public fixture/reseed endpoint; report export contains no raw credentials.

## Phase 7 — measured capacity and integration
Run small smoke load, then 1k and 10k actors. Attempt 50k distinct identities only if generator/service resources allow. Use arrival-rate workload to avoid silently reducing load when responses slow. Include auth provisioning timing separately, entry bursts, status polls and confirmations. Monitor generator CPU/memory, scheduled/achieved iterations, dropped iterations, active clients, connections and RPS.

Compare repeated draws with matched settings and sensible intervals. Direct same-manifest/same-seed tests prove request-independence; sampling charts alone do not. Query actual integrity across transitions, not just final seat count.

Gate: fresh checkout starts with documented commands; real checks pass; resource/config/limits recorded; reports distinguish 50k population from concurrency; normal profile disables lab and seed fixtures; production frontend cannot choose mocks.

## Phase 8 — defence and demonstration
Each person rehearses whiteboard.md answers against their actual code and limitations. P4 writes a five-minute demo/reset script. Show judge entry/receipt, duplicate request, draw, recovery, confirmation, proof and measured comparison. Small live run plus larger saved reports is acceptable if labelled.

Customer-facing release gate: human owners record actual understanding/review and operational limitations. This is an accountability step, not a demand to memorize functions. A demo may run before a production review, but cannot claim production readiness.

## Suggested time allocation
For any hackathon duration: about 10% foundation/contracts, 40% working core/security slice, 25% product/lab completion, 25% integration/evidence/rehearsal. Adjust based on actual progress. Commit throughout; do not defer merging all branches until the final hour.

## Session handoff
At the end of an implementation checkpoint, update your progress record and report files changed, behaviour completed, exact checks, remaining blockers and next action. Central memory records integrated truth, not all branch aspirations.


## Four-member task distribution

Use one integration branch and four feature branches/worktrees. P1's bootstrap is the shared starting commit. No member builds a second application. The names P1–P4 are assignments; replace them with teammate names when known.

| Member | Main work | Owned implementation paths | Required handoff |
| --- | --- | --- | --- |
| P1 — Core and contract | Shared models/migrations, drops/entries, organizer domain routes, draw, offers/confirm/expire/promotion, proof, audit | backend/app/core, persistence, drops, allocation, audit; backend/alembic; backend/tests/core; backend/app/main.py; backend dependency files; contracts | Bootstrap hash; exact API/encoding; migration/worker commands; real integrity results |
| P2 — Security | Credentials/sessions/profile, CSRF, object/role authorization, shared rate limits, safe degraded writes | backend/app/security; backend/tests/security | Mounted helper interfaces; cookie/CSRF flow; provisioning interface; limits/outage/security results |
| P3 — Frontend | Public and participant UI, organizer controls, proof verification UI, lab/dashboard views, typed API, design/accessibility | frontend including dependency/lock files | Real endpoint integration; all state/error behavior; responsive checks; stable accessible E2E locators |
| P4 — Lab and integration | Docker/Nginx, runner/lab API, scenarios, reports, performance/E2E, deployment/reset/demo, merged progress | backend/app/lab; tests/performance; tests/e2e; scripts; infra; compose.yaml; Makefile; .env.example; operational README; reports; memory.md after handoff | Fresh-checkout startup; matched measured comparison; DB-audited reports; actual workload/limits; demo script |

Each member owns their progress/person-N.md when coding starts. P1 initially owns memory.md; P4 becomes its sole writer at bootstrap handoff. Shared models/migrations/contract changes go through P1 even when requested by P2/P4. Frontend fixes go through P3. The member ownership map in architecture.md must match this table.

P1 has the heaviest correctness work: prioritize the vertical slice and expiry/recovery before optional exports or UI extras. P2 and P4 prepare security model fields/config interfaces during bootstrap; P3 prepares layouts against the committed fixtures. After the checkpoint they implement in parallel. If a critical path is blocked, explicitly transfer a bounded task and pause other writers for those files.

If using two Codex and four Antigravity workspaces: Codex 1 can implement P1, Codex 2 P2; Antigravity 3 implements P3 and Antigravity 4 P4; Antigravity 1/2 can perform read-only core/security reviews. They report reproducible findings to the owner. Extra AI workspaces do not create extra file owners or authorize simultaneous edits.

## 24-hour execution budget

This schedule is a planning target, not evidence of completed work. Keep phase gates even if timings move.

| Hours | Team checkpoint |
| --- | --- |
| 0–2 | Read/agree pack; P1/P2/P4 settle models/interfaces; P1 commits bootstrap; P3 prepares UI shell |
| 2–6 | P2 real sessions/CSRF/authorization; P1 drops/entry/receipt; P3 login/entry UI; P4 runnable Compose and smoke harness |
| 6–10 | First real login-to-confirmed-ticket slice; commitment, snapshot, fixed rank and first offers |
| 10–14 | Expiry/promotion, race/restart tests; organizer controls; proof UI; lab run/report plumbing |
| 14–18 | Matched FCFS comparison, bounded attack scenarios, metrics/report checks; finish essential UI states |
| 18–21 | Merge and fresh-checkout verification; 1k/10k workload, attempt 50k only with headroom; fix critical bugs |
| 21–24 | Freeze features, demo/reset/rehearsal, actual memory/whiteboard evidence and submission |

If behind: defer PoW/risk experiments, external randomness, notification extras and advanced charts first. Preserve secure identity/ownership, unique durable entries, capacity integrity, confirmation/expiry/recovery, real participant flow, proof and one measured comparison. List unimplemented requirements openly; do not fill gaps with fake API success.

## Copyable AI launch prompts

These prompts authorize coding inside the assigned repository. They do not create extra agents automatically. At any new chat also read actual memory.md if it exists and inspect relevant code. A newly generated project is not claimed runnable until verified.

### Member 1 prompt — bootstrap, core, allocation and proof

```text
You are P1, the core and shared-contract owner of our single FairDrop application.
Read rules.md, prd.md, architecture.md, phases.md and whiteboard.md. Read memory.md
if present and inspect the existing repository. Use this pack as the canonical
merged specification. Preserve useful existing code; report conflicts explicitly.

First deliver Phase 0: shared monorepo, compatible pinned dependencies/locks,
complete SQLAlchemy models and Alembic migration, typed errors/API DTOs, complete
OpenAPI plus significant-state/error fixtures, security and lab interface stubs,
fixed main.py imports, actual health capabilities and frontend type-generation
command. Coordinate model fields with P2 and services/env with P4. Stubs fail
explicitly; deny-by-default auth; no fake successful writes. At the first actual
code edit, copy memory.template.md to memory.md and record only observed facts.
Publish a checked bootstrap commit hash and handoff before independent module work.

Then build your owned core/persistence/drops/allocation/audit modules: public
metadata, owned organizer drafts/grants/publish/cancel, durable unique entry,
receipt/history, atomic close/snapshot, committed seed, canonical HMAC ranking,
timed offers, confirm/expire, fixed-rank promotion, restart reconciliation and
public-safe proof. Use the exact architecture.md API paths and encoding.
Prioritize the real login -> entry -> draw -> offer -> confirm -> refreshed ticket
slice. Use PostgreSQL constraints, documented lock order and clock_timestamp()
after locks. Same keys, different keys, retries, replicas and worker restarts
cannot bypass identity/slot invariants. Never regenerate the draw after failure.

Use P2 security and P4 infrastructure interfaces; do not implement another auth
system or frontend. Own shared migrations/contracts and coordinate all changes.
After default LOTTERY passes, add isolated safe FCFS_DEMO with same admission,
uniqueness/ownership defenses and explicit arrival-order allocation.

Run meaningful tests on real PostgreSQL for duplicate entry, closure race,
capacity, confirm/expire, repeated draws and restart/promotion. Supply the
standalone verifier. Update progress/person-1.md and whiteboard evidence; hand
central memory ownership to P4 after bootstrap. Report exact code/checks/blockers
and continue implementation within scope instead of stopping at a plan.
```

### Member 2 prompt — security, sessions and abuse handling

```text
You are P2, the security owner in our existing FairDrop repository.
Read rules.md, prd.md, architecture.md, phases.md, whiteboard.md, current memory
and committed OpenAPI/fixtures. Wait for the shared bootstrap for implementation;
you may prepare model/config/interface requirements with P1 before it.

Own backend/app/security and backend/tests/security. Implement provisioned access
credentials, stable-account opaque sessions stored as digests in PostgreSQL,
GET session/CSRF, logout, profile, Origin/CSRF enforcement and role/object-owner
checks. Same account on multiple devices is one entry identity. Consume P1's
shared models; propose schema/migration changes to P1. Expose the exact mounted
security interfaces agreed in architecture.md. Core and lab use these helpers.

Implement atomic Redis limits across account, session, action/endpoint and cautious
network/global budgets, with verified shared state across two replicas. Never
trust arbitrary forwarded headers or collapse campus Wi-Fi into one participant.
Never use harness bot labels in security decisions or alter accepted draw odds.
No default PoW, /24 weighting, fingerprint identity or suspicion demotion.
Optional admission experiments are isolated and visibly labeled.

Keep cookies HttpOnly/SameSite/Secure under TLS; use documented local demo exception.
Redact credential/token/CSRF material. Enforce documented Redis-outage behavior:
safe DB-backed authorized reads continue; protected writes fail explicitly with
retryable 503; persisted entries/sessions/seats survive. Record availability costs.

Run actual expiration/revocation, multi-device, CSRF/Origin, cross-account/drop-owner,
profile privilege, guessing/limiter, shared-IP, multi-replica and outage checks.
Deliver cookie/config/provisioning handoff to P1/P3/P4. Update your own progress
record and WB-03/WB-04/WB-09 evidence. Continue through real integrated login/API
flows; no separate app, placeholder success or invented test result.
```

### Member 3 prompt — full frontend

```text
You are P3, the sole frontend owner for our single FairDrop website.
Read rules.md, prd.md, architecture.md, phases.md, design.md, whiteboard.md, actual
memory and bootstrap OpenAPI/fixtures. Work in frontend only plus your progress
record and coordinated design updates. Do not invent backend routes or identity.

Use React/TypeScript/Vite, the specified router/query/forms/design stack, generated
OpenAPI types and one API/error/CSRF client. Build public landing/discovery/detail,
invitation sign-in, history/profile/logout, saved receipt, draw/waitlist/offer,
confirmation/ticket/expiry/cancellation and verifier. In the same app implement
organizer draft/grants/publish/cancel/audit/inventory plus lab controls/reports.
Prioritize real login -> entry -> receipt -> confirmation -> refreshed ticket.

Use architecture.md exact API routes; frontend /organizer intentionally calls
/api/v1/admin. Session cookies and server authorization are authoritative. No
bearer tokens/credentials in localStorage. Handle loading/empty, validation,
uncertain timeout, offline, 429/backoff, 503, forbidden and not-found explicitly.
After timeout reconcile server state and retain the mutation key for retry.
A timer refetches; it never locally awards/expires a seat. Rank is null pre-draw.

Use design.md tokens, responsive ticket panels, accessible forms/focus/tables,
server-corrected deadlines/timezones and conditional jittered polling. Show
measured metrics only with run provenance; unavailable means unavailable. An
explicit development fixture adapter cannot be selected in the production build.
No random traffic points, fake winner, dummy export or decorative dead button.

Verify 360/768/1280px, keyboard path and real participant/organizer flows. Give P4
stable accessible E2E locators. Coordinate missing endpoints with P1/P2/P4 instead
of fabricating them. Update progress/person-3.md and WB-06 evidence with actual
checks. Deliver integrated functioning UI, not just screens.
```

### Member 4 prompt — attack lab, infrastructure and integration

```text
You are P4, the lab, infrastructure and integration owner of shared FairDrop.
Read the pack, architecture.md exact API/report contract, bootstrap, current memory
and all member progress. Own lab module, scripts/infra/Compose, performance/E2E,
reports, operational README and central memory after P1 hands it over.

Build same-origin Nginx/static frontend, api-a/api-b, PostgreSQL persistent volume,
Redis and the durable worker. Agree readiness/degraded routing with P2. Provide
verified locked-install/migrate/private-seed/start/test/reset instructions. Normal
profile disables lab/FCFS/fixture seeding; destructive demo reset is explicit.
Do not modify P1/P2 business logic to make tests green.

Implement organizer-owned demo-only lab API, bounded allowlisted scenarios, one
active runner, fixed configured target, cancellation/timeouts/progress/report
persistence and safe subprocess argv. Normal API HTTP traffic performs measured
entries/confirmation; setup provisioning is outside load timing. Bot labels stay
in the harness. Never accept arbitrary URL/script/command from the browser.

Run normal, early-bot, retry-flood, credential-farm, controlled shared-IP,
reconnect/lost-response, worker restart, Redis failure and expiry-race scenarios.
Compare safe FCFS_DEMO and LOTTERY with matched cohort/credentials/limits/capacity
and documented policy timing. Validate reports against DB state. Follow prd.md
metric definitions: admission, initial offers, promotions and confirmations are
separate; undefined statistics have reasons. Preserve source summary as supplied,
small and unreproduced; never reuse it as a new benchmark.

Record scheduled/delivered/dropped work, achieved RPS, clients/connections/inflight,
endpoint/status latency, expected 4xx/unexpected 5xx, hardware/generator limits,
identity vs actor share, integrity and trial uncertainty. Start small, then 1k/10k;
attempt 50k only with resources. Database population is not concurrency evidence.

Build real Playwright participant/organizer journeys, coordinate reproducible
owner fixes, run a fresh-checkout integration and proof verifier. Maintain memory
from merged commits/checks, not branch aspirations. Deliver actual reports,
known limits and five-minute demo/reset script. Update whiteboard evidence;
humans alone record their understanding/review. Continue to verified integration.
```

## Final integration checklist and demo

- Locked installs, migrations and private seed work from a fresh checkout.
- Both API replicas share session identity/limiter state; proxy routes/cookies/CSRF work.
- Real participant login, saved receipt, offer confirmation and recovered ticket work.
- Organizer grants are draft-only; published rules lock; ownership is enforced on all routes.
- Same/different-key concurrent mutations and close/confirm/expire races preserve invariants.
- Worker kill/restart resumes the same draw/cursor; verifier reproduces it.
- Report uses delivered real traffic and matches DB counts; lab stops safely and is disabled in normal profile.
- Production frontend cannot use fixtures; secrets/private identities do not leak; errors and mobile/keyboard paths work.
- Actual checks/blocked checks, commit and demo limits are recorded; no invented human review.

Five-minute demo: (1) show measured early-bot FCFS result; (2) replay matched FairDrop workload; (3) enter/retry and refresh one account with one receipt; (4) confirm one offer and expire another to show promotion; (5) verify proof and show inventory/admission/performance evidence. Use a small live run and clearly labeled larger saved reports if needed. Never pre-fill favorable metric numbers.
