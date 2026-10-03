# FairDrop — whiteboard defence

Build pack: FairDrop merged specification v1.0 · 2026-10-03.
Status: specification only; no code, benchmark, completed phase or human review is claimed.
Status: proposed design explanation. No system is claimed shipped or reviewed.
Purpose: humans and AI must explain customer-facing behaviour, decisions, malicious actors, data structures and failure boundaries. This is high-level accountability, not function-name memorization.


## The whiteboard defense benchmark

This file serves humans and AI. Its purpose is to make the shipped high-level design explainable and defensible. Use the user's benchmark:

> I should be able to pull you aside at any moment and ask you to explain any customer-facing system you've shipped. You should be able to clearly explain how it works and defend the decisions you made. This is my benchmark for responsible AI usage.
>
> I don't expect line-level familiarity with the code. I don't care if you remember the exact function name or implementation detail. You may not even know it. I don't care.
>
> But if I ask "why did you do X instead of Y?", "what happens if this actor behaves maliciously?", "what data structure did you use here and why?", or "where does this fail?" you should be able to answer confidently.
>
> For PoCs, demos, experiments, whatever: I don't care. Generate 100% of it and understand none of it. Speed over quality every time in those specific scenarios.
>
> But if you're shipping customer-facing work, you can't be shipping things you don't understand at a high level.

For this hackathon, isolated experiment code may be rough. Preserve truthful demo claims. If a feature is offered to actual customers, its accountable human must understand its high-level behavior and failure modes. This is a release benchmark, not a demand to memorize implementation names or obtain permission for every code edit.

## 1. How to use
Before implementation use these entries to understand the proposed system. After code changes, the owner updates the affected answer and attaches concrete implementation/test evidence. Humans then explain it back in their own words. An AI cannot record a human's understanding on their behalf.

For an isolated experiment, speed can take priority. Before experimental code becomes a customer-facing path, its assumptions and failure modes must be understood and verified. Do not confuse a hackathon demonstration with operating a public paid-ticket service.

Read this alongside architecture.md and whiteboard.md (Research merge and evidence). If code differs, document the difference and resolve the spec; never rehearse an answer that no longer matches behaviour.

## 2. System in 60 seconds
FairDrop accepts one eligible entry per provisioned account during a published window. PostgreSQL saves that entry before acknowledging it. At the deadline, the server freezes the list. A persisted seed and canonical algorithm rank the entries, and up to capacity seats become timed offers. Participants confirm their own offers; expired offers move to the next unoffered entry in that original order.

Authentication/session limits protect access. Rate limits reduce expensive repeated traffic. They do not award extra lottery chances or weight accepted entries. Sessions and seats survive process restarts because the durable truth is in PostgreSQL.

The browser displays this state, reconciles after network failures and never decides that a seat exists. A separate isolated test lab exercises real endpoints and reports both admission availability and selection outcomes.

## 3. Decision register
| ID | Decision | Owner | Evidence/review status |
| --- | --- | --- | --- |
| WB-01 | Timed equal-entry draw | P1 | Proposed; tests/review pending |
| WB-02 | PostgreSQL seat/entry authority | P1 | Proposed; tests/review pending |
| WB-03 | Durable invitation-based sessions | P2 | Implemented on feature/m2-security (backend/app/security/sessions.py, provisioning.py, csrf.py); tests in backend/tests/security |
| WB-04 | Layered limits; shared-IP caution | P2 | Implemented on feature/m2-security (backend/app/security/limits.py Lua sliding window); tests in test_limits.py |
| WB-05 | Commitment/reproducible proof | P1 | Proposed; tests/review pending |
| WB-06 | Server-driven client recovery | P3 | Proposed; tests/review pending |
| WB-07 | Isolated real HTTP attack lab | P4 | Proposed; tests/review pending |
| WB-08 | Fixed ranking and expiry recovery | P1 | Proposed; tests/review pending |
| WB-09 | Evidence and identity-abuse limitation | P4 + P2 | Proposed; tests/review pending |
| WB-10 | Mock checkout and commercial boundary | Team | Explicit scoped decision |

## WB-01 — Why a draw rather than first come?
Answer: First-come allocation rewards arriving before others. A time window followed by equal-entry ranking removes order from the rank calculation for accepted identities. It also separates 50k entry writes from the small number of actual seat ownership changes.

Alternative: FIFO is simple and can be inventory-correct but keeps speed advantage. Per-IP lottery weighting might discourage some farms but can punish legitimate networks. Weighted policies stay outside the default equal-entry claim.

Where it fails: A user who never gets an accepted entry cannot participate. Flood resistance and admission opportunity therefore require separate measurements. A late entrant after the deadline is excluded, even with a slow connection.

Data structure: unique entry relation + immutable manifest + ordered rank table.
Evidence to attach: same-manifest/same-seed identical ordering despite changed arrival/retry patterns; admission tests.

## WB-02 — How can overselling be impossible within the model?
Answer: Exactly capacity slot rows exist. A slot has one current owner, and transactions/unique constraints guard active ownership. API instances and workers all modify the same database state. A counter in a browser or Redis is not the authority.

Alternative: In-memory decrement loses coordination across replicas/restarts. Redis-only inventory adds a separate recovery/consistency problem. Check-then-write without locks/constraints races under concurrent requests.

Where it fails: Broken migration, bypassed write path, inconsistent redundant state or database loss. "No oversell in tests" is evidence, not immunity to all future coding mistakes.

Data structure: seat-slot relation, active reservation uniqueness, audit history.
Evidence: concurrent offer/confirm tests and queries across transitions, not only final totals.

## WB-03 — What identifies a participant?
Answer: A provisioned access credential authenticates a stable account, and a per-drop eligibility grant permits entry. Different tabs/devices for that account still map to one unique entry. Durable sessions are opaque cookies with server-side state.

Alternative: Browser sessions alone allow multiple entries by clearing cookies. IP uniqueness excludes shared Wi-Fi. Email/phone control raises friction but does not prove a unique person.

Where it fails: A stolen credential can impersonate its owner; an attacker with multiple qualifying grants gets multiple entries. Revocation/recovery and provisioning integrity matter. The initial demo does not establish unique humans.

Data structure: user, credential digest, session, eligibility grant.
Evidence: same identity across devices; session expiration/revocation; cross-account denial; credential farm scenario.

## WB-04 — What if an actor sends 10,000 requests?
Answer: One authenticated identity still has one entry; duplicate requests do not modify rank. Shared atomic limits reduce work per identity/session/endpoint. Coarse network/global budgets protect service resources while preserving independent identities.

Alternative: IP-only rules fail under both proxy rotation and campus NAT. Requiring proof-of-work can favour faster devices; it is not the default fairness mechanism.

Where it fails: Distributed volumetric attacks can overwhelm network/infrastructure before application rules run. Redis outage degrades protected writes. Aggressive limits can deny legitimate admission, which reports must show.

Evidence: actual duplicate flood, multi-replica limiter, shared-IP cohort, admission latency and denial rates.

## WB-05 — Can the organizer rig the draw?
Answer: The seed is committed before publication, the manifest is committed at closure, and revealed material reproduces the ranking afterward. This detects changes relative to the published commitments.

Limitation: An organizer controlling the seed and service could search seeds or selectively abort; simple commit/reveal does not prevent that. Independent future randomness after manifest commitment would reduce that control, but also needs a specified outage/abort policy.

What we say: "Reproducible and auditable draw", not "unriggable lottery."
Evidence: commitment/ranking verifier, privacy check, one draw per drop, no public reseed interface.

## WB-06 — What happens when a participant refreshes or a response is lost?
Answer: The accepted entry lives in the database. Re-authenticated /me returns it. If the write committed but its response was lost, the same operation key or state reconciliation recovers the domain result. Closing a tab does not cancel it.

Alternative: LocalStorage-only state can be lost/forged and differs across devices. Button disabling reduces accidental clicks but does not defend backend concurrency.

Where it fails: Request never committed, database unavailable, session/credential revoked or offer expires while offline. Do not promise a saved entry before receipt confirmation.

Evidence: lost-response-after-commit test, refresh/reconnect browser test, two tabs.

## WB-07 — Are the attack charts real?
Answer: Runner clients call ordinary authenticated endpoints over HTTP. The harness records ground truth and workload; the backend does not receive bot labels. Reports combine delivered load with committed outcomes and disclose scale/hardware.

Alternative: A visual simulation is useful for teaching but is not load evidence. Seeding 50k rows is not 50k concurrent connections.

Where it fails: Generator saturation, dropped iterations, simplistic bot model, one-trial sampling or unrealistic network distribution. The attached source summary has these scope limitations and is labelled accordingly.

Evidence: run manifest, target, hardware, scheduled/achieved work, dropped iterations and DB audit.

## WB-08 — Who gets an expired seat?
Answer: The next eligible unoffered entry from the same persisted ranking. Confirmation and expiry lock the authoritative records in the same order and read fresh database time after locking. A late confirmation cannot steal a promoted seat.

Alternative: Rerandomizing each promotion changes the original fairness explanation; in-memory cursors can skip/repeat participants after restart.

Where it fails: Deadline availability, worker lag, exhausted waitlist or a bug in cursor/ownership transactions. Reconciliation handles process crashes, not arbitrary data loss.

Data structure: rank table, durable promotion cursor, reservation state machine.
Evidence: deadline race, worker kill mid-promotion, monotonic cursor and exactly-one ownership tests.

## WB-09 — Why not deploy the source report's /24 weighting?
Answer: The report gives every simulated human a distinct /24. Real colleges and workplaces share networks. A policy evaluated without those humans cannot establish its fairness for them. Suspicion demotion also changes equal-identity odds.

Keep historical experiments separate. Evaluate false exclusions/shared-network effects before any policy change. Default draw treats accepted eligible identities equally; limits are reported as admission controls.

Where it fails: Even equal per-identity probability cannot prevent a many-credential attacker increasing their aggregate share. Stronger qualification/provisioning is a separate problem.

Evidence: the Research merge and evidence section below, mixed shared-network scenarios, repeated matched trials and actor-versus-credential metrics.

## WB-10 — Is this a real paid-ticket system?
Answer: It is a working persistent registration/reservation website with simulated confirmation. It does not collect money. This lets the hackathon prove allocation behaviour without incorrectly presenting a payment prototype as financial settlement.

Before real selling: integrate authenticated provider webhooks, durable payment/refund states, reconcile late payment with expired offers, define cancellation/refund policy, strengthen eligibility/recovery, review privacy/operations and test failure handling. These require their own design defence.

## 4. Malicious actor walkthrough
| Actor action | Expected behaviour | Residual risk |
| --- | --- | --- |
| Repeat entry with new keys | Same unique entry | Service work still needs limits |
| Open many tabs | Same identity/result | Extra read traffic |
| Forge reservation ID | Ownership denial | Stolen valid session still matters |
| Modify browser countdown | No effect on DB deadline | Confusing local display |
| Rotate IPs with same account | Same account quota/entry | Distributed network load |
| Obtain multiple valid credentials | Multiple identities unless provisioning catches it | Sybil advantage remains |
| Guess organizer endpoints | Server role and owner denial | Compromised organizer account |
| Submit arbitrary lab URL/script | Rejected; fixed target/allowlist | Lab privileged resources need caps |
| Crash worker | Same persisted ranking resumes | Longer wait/DB outage |
| Exploit shared Wi-Fi | Independent eligibility; no identity collapse | Coarse limits can affect admission |
| Cause Redis outage | Explicit protected-write degradation | Some deadlines may be missed |

## 5. Human review record — to fill after implementation
For each decision add: accountable teammate, implemented commit/path, relevant tests/report, actual behaviour, remaining limit, reviewer/date and explanation given. Leave it pending until performed.

Suggested questions:
- Which operation creates a seat and which only displays it?
- At exactly the closing deadline, what determines entry acceptance?
- Why is rank stored rather than regenerated after restart?
- What happens if confirmation and expiry run together?
- What does the seed commitment prove, and what does it not prove?
- How many identities can one actor obtain?
- Does a Redis failure erase my entry?
- What exactly does the 50k graph measure?
- Which screen or feature uses demo data?
- Where would this fail outside the tested workload?

## 6. Customer-facing release benchmark
A human responsible for each surface can explain its behaviour, alternatives, malicious actors, data structures and limits. They need not know exact function names. An unresolved invariant/security failure blocks release. A hackathon demo can remain scoped/experimental, but public claims must match actual evidence.


## 7. Research merge and evidence

| Research element | Merged decision | Reason |
| --- | --- | --- |
| Timed entry and random allocation | Canonical LOTTERY default | Removes arrival/repetition from ranking for accepted identities |
| PostgreSQL durable truth | Canonical entry/session/seat authority | Shared transactions, constraints and process recovery in one model |
| Redis/Lua inventory suggestion | Redis only for atomic ephemeral limits/cache | Avoids a second authoritative inventory and recovery protocol |
| Aggressive bot detection | Explainable admission limits and optional lab experiments | Protect availability; expose false exclusions/friction |
| PoW | Optional isolated admission experiment | Hardware/latency burden needs measurement; no production requirement |
| /24 weighting and suspicion demotion | Historical/offline experiments only | Change accepted-identity probabilities and can punish campus networks |
| Attacker scenarios and metrics | Adopt and extend in real HTTP lab | Strengthen demonstrable adversarial behavior |
| Request-independent fixed ranking | Persist all ranks and promote from them | No redraw or favorable retry after expiry/restart |
| Four separate technology apps | One React/FastAPI monorepo | Shared identity/contracts/components prevent integration drift |
| Bot-win <5% / Jain >.95 targets | Replace with cohort rates, uncertainty and deterministic gates | Valid bot-controlled credentials may legitimately win; one trial fluctuates |

Original summary provenance: 400 simulated humans, 40 seats, 3.5-second entry window, 2.5-second hold, one trial per condition; each human has a different /24. It reports 28 passing integrity runs and revealed-seed replay, but source implementation/raw traces/hardware were not supplied for independent reproduction here. These are supplied historical claims. The tiny windows are simulator settings, not normal user deadlines.

Its distinct-network humans do not test shared-campus fairness; clustered bots do not prove distributed-attack resistance. Some zero-bot outcomes may result from admission blocking or changed weights. A reported 1.20x stealth-bot advantage and 32.5% sold-unit bot share illustrate why the summary cannot support "zero bots win." No historical values are new measured FairDrop benchmarks. Keep supplied reports visibly labeled and separate from safe-FCFS matched results.

## 8. Data structures and transaction defense

| Structure | Why we chose it | Cost and failure boundary |
| --- | --- | --- |
| Unique indexed entries | One durable accepted account/drop record | DB write load; eligibility quality remains external |
| Publication-locked grants | Known allowed accounts before entry opens | No self-service public signup or late grants in v1 |
| FrozenEntry relation | Immutable membership tied to one draw | O(N) storage; cannot prove excluded attempts were admitted |
| HMAC scores + persisted DrawRank | Reproduce a pseudorandom total order and waitlist | O(N log N) sort, O(N) storage; server-operator trust remains |
| SeatSlot + partial-unique Reservation | One current account/slot owner; retain expired history | Coordinated DB transactions; mutation paths must preserve same-drop FKs |
| Durable cursor | Crash-safe next unoffered rank | Cursor and new offer must commit together |
| Session/IdempotencyOperation | Revocation and uncertainty recovery across replicas | Credential theft and DB outage remain risks |
| Redis token buckets | Bounded shared ingress work | Temporary quotas reset on Redis loss; protected writes degrade |

Entry deadline uses `starts_at <= clock_timestamp() < ends_at` after shared drop locking. Close takes the conflicting exclusive lock and includes committed accepted entries; it does not silently filter users based on later credential revocation. Seat changes use Drop -> SeatSlot -> Reservation locks and fresh wall clock. At exact offer expiry, confirmation is too late. Row lock waiting cannot make a transaction-start timestamp a valid deadline check. A process death rolls back uncommitted changes; committed changes are reconciled from durable facts.

This simple serialized per-drop seat coordinator is a deliberate scope tradeoff: at most 500 seats with many more compatible entry admissions. It is not a universal throughput architecture. Measure contention; optimize only with evidence while preserving consistent locking and original-rank promotion.

## 9. Per-feature defense record (fill after coding)

| Decision | Accountable human | Implementation commit/path | Executed check/report | Actual limit | Human explanation/review |
| --- | --- | --- | --- | --- | --- |
| WB-01/02/05/08 | P1 | Pending | Pending | Proposed design only | Pending |
| WB-03/04 | P2 | Pending | Pending | Proposed design only | Pending |
| WB-06 | P3 | Pending | Pending | Proposed design only | Pending |
| WB-07/09 | P4, with P2 for identity | Pending | Pending | Supplied evidence unreproduced | Pending |
| WB-10 | All four | Scope: simulated checkout | No money collected | No payment/transfer/check-in security | Pending |

AI may suggest answers, update accurate implemented behavior and attach actual evidence. Only a human supplies their own explanation/review record. Ask each owner to explain: why this alternative, what malicious actor can do, which durable structure matters, what happens at the deadline/outage, what was actually tested, and where the guarantee stops. A confident answer without matching implementation is not a successful defense.


## M1 implementation evidence — 2026-10-03T17:53:42.031585Z

Implemented on branch M1; last tested core commit `f644645ac0ae8390727871cd657a09c9b6e5dcbb`. Not merged to main.
User directed M1-only push and no M2 integration. All human explanations/reviews remain
PENDING. Specification/rehearsal text above is not a claim of integrated release.

| Decision | Implementation | Executed evidence | Remaining limit / human review |
| --- | --- | --- | --- |
| WB-01 | 803e068 durable identity/drop entry; 20775f3 frozen HMAC ranking | Same/different-key concurrency, one acceptance audit, same-input/request-order ranking | Admission controls are separate; P2 real identity/limiter integration pending; review PENDING |
| WB-02 | Reservation authority, composite FKs/partial indexes, atomic slots; f9d4abc ownership transitions | Capacity/active-owner checks, direct cross-drop/user FK rejection, concurrent confirmations | 500-seat configuration ceiling is not a measured load claim; review PENDING |
| WB-05 | AES-GCM protected committed seed; sealed snapshot/ranks; c65bc3e public proof/stdlib verifier | Canonical byte reproduction, immutable proof rows, tampering/privacy/participant inclusion tests | Server operator seed-search/selective cancellation remains possible; review PENDING |
| WB-06 | PostgreSQL operation claim + fingerprint + domain reference; own /me and receipt recovery | Concurrent/replayed entries and confirmed reservations resolve same objects, late accepted retry works | P3 browser refresh/lost-connection journey and P2 sessions still pending; review PENDING |
| WB-08 | Fresh clock after Drop -> Slot -> Reservation locks; fixed rank cursor and worker | Both confirmation/expiry outcomes, exact promotion, SIGKILL during draw/offer/promotion and real worker restart | Process recovery does not prove host/storage recovery; review PENDING |
| WB-09 | 3536139 demo-only admission-order comparator with shared inventory/admission/confirmation rules | FCFS order, retries, expiry/promotion, null lottery evidence and normal-profile isolation | No measured matched-cohort/load chart yet; P4 owns that evidence; review PENDING |

Final core suite: 27 passed using real PostgreSQL 18.6 / Python 3.12.14, with an
explicit test-only security adapter. Fresh migrations/consistency and downgrade-upgrade,
OpenAPI/schema fixtures, TypeScript compilation, API socket smoke and worker entrypoint
passed. Exact commands and known initial failures are in progress/person-1.md and
contracts/HANDOFF.md. No raw credentials or unrevealed seed were recorded here.
