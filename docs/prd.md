# FairDrop — Project Requirements Document

Build pack: FairDrop merged specification v1.0 · 2026-10-03.
Status: specification only; no code, benchmark, completed phase or human review is claimed.
Status: proposed specification; not yet implemented.
Canonical product name: FairDrop. Public subtitle: Fair Drop — fair seat allocation.


## Build pack and single source of truth

The two research tracks are merged into one policy: a durable equal-entry lottery as the default, with the stronger attack scenarios, measurements and optional anti-abuse experiments in an isolated lab. No second backend or alternative production fairness policy is implied.

| File | Question it answers |
| --- | --- |
| prd.md | What are we building, for whom, and what counts as done? |
| architecture.md | How does it work, what owns state, where is code, and what is the exact API? |
| rules.md | How must humans/AI code, handle errors and respect boundaries? |
| phases.md | What is built next, who owns it, and how does each member instruct AI? |
| design.md | What should every screen look like and how should states behave? |
| whiteboard.md | Can a human explain the decisions, attacks, structures and limits? |
| memory.template.md | How is actual progress recorded after implementation starts? |

This is a seven-document package. `memory.template.md` is not a progress log. P1 copies it to `memory.md` at the first code edit, fills actual facts, and transfers integrated-memory ownership to P4 after bootstrap. No phase is complete at document preparation time.

Copy these files into the shared repository root. Older attached PRDs, architecture drafts and member prompts are reference material; retire conflicting active copies. Preserve useful existing implementation and report specific discrepancies instead of overwriting it to match a guess. At a new session read rules.md, memory.md if present, assigned phase/ownership, the relevant architecture contract, and then relevant code. Full ownership and four copyable launch prompts are in phases.md.

Requirements live here, system/API policy in architecture.md, workflow in rules.md, visuals in design.md, execution order in phases.md, and rationale in whiteboard.md. Generated OpenAPI must implement the agreed contract; it cannot silently override product policy. Memory records observed progress, never new requirements. When a conflict appears, coordinate the change and update all affected sections in the same handoff.

## 1. Purpose
Build a high-demand event/registration website that allocates limited seats without granting more chances to faster or more repetitive clients. The demonstration target is 500 seats and up to 50,000 distinct participant identities, subject to measured delivery on the available hardware.

The central promise is: one eligible identity, one entry, equal initial draw treatment. Entry acceptance, allocation correctness, availability under attack and identity abuse are distinct concerns and must be measured separately.

## 2. Target users
| User | Need | Primary experience |
| --- | --- | --- |
| Participant/student | Enter without racing bots; retain state after refresh | Discover, verify invitation, join, receive receipt, confirm |
| Event organizer | Manage a limited-seat drop reliably | Configure, publish, monitor, audit |
| Platform administrator | Operate demo accounts and infrastructure | Credential provisioning, access policy and operational tools |
| Judge/reviewer | Inspect behaviour and challenge claims | Attack lab, reports, verifier, whiteboard defence |

Potential applications: college events, workshop registrations, concerts, limited-access programs and product reservations. The initial implementation is a seat-registration product. Shipment, resale and financial settlement are outside the hackathon core.

## 3. Fairness policy
- Accept one durable entry per eligible identity per drop during the published window.
- Acceptance requires a valid session and an invitation eligibility grant for that drop.
- At closure freeze the accepted eligible entries atomically.
- Rank that fixed list using the documented pseudorandom draw.
- Offer up to capacity seats, then promote from the same ranking when offers expire.
- Entry time, request volume, browser type and risk score do not affect the rank of an accepted eligible identity.
- Rate limits protect admission/availability; they do not award extra lottery chances.
- No network-cluster weighting, suspicion demotion or proof-of-work is enabled in the default draw.
- Additional genuine credentials increase an attacker's identity share. The system does not establish unique humanity from an IP or email.

Success means demonstrated request-independence and allocation integrity under stated conditions, not zero bot selections in every trial.

## 4. Product surfaces and required features
### Public website
Landing page with a concise value proposition, how selection works, featured public drops and links to rules/verification. Search/filter paginated drops by title, category and phase. Detailed event page with organizer, capacity, location/online indicator, schedule, entry window, confirmation policy, eligibility requirement and cancellation state. No private draft content leaks.

### Participant workspace
Invitation-access sign-in, secure persistent session, profile display-name/timezone settings, My Entries history, entry receipt, draw-pending state, offer countdown, simulated confirmation, confirmed ticket, waitlist, expiry/cancellation explanation and audit verifier. Logout is real and revokes the current session. A browser refresh or second authenticated device recovers the same principal and entries.

Use honest copy: "Invitation verified." This is not "Human verified." A global access credential authenticates a principal; separate drop eligibility grants restrict which drops they may enter. Organizer provisioning is described in architecture.md.

### Organizer workspace
Owned-drop dashboard, draft creation/editing, scheduling/publication, cancellation before allocation, entry counts, lifecycle status, inventory monitor, draw trigger/recovery controls, pseudonymous participant export, audit history and report access. Server authorization enforces ownership. A platform administrator may access all drops; an ordinary organizer may not edit another organizer's drop.

Capacity, eligibility rules, draw mode and timing lock at publication. After publication only descriptive copy can change through an audited edit. Short demo windows are configured before publication; no retroactive shortening to favour winners.

### Attack laboratory
Organizer-authorized, isolated demo/test profile only. Allowlisted normal, early-bot, retry-flood, multi-credential, shared-IP, reconnect, race and worker-failure scenarios. Adjustable bounded actor counts, rates, durations and retry patterns. Start/stop, progress, run history, measured report comparison and export. Never accept an arbitrary target URL from a browser.

### Audit and explainability
Persistent entry receipt, public pseudonymous manifest commitment, disclosed algorithm/version, post-freeze seed reveal and verifier. A human can explain the state machine, identity limitation and transaction boundaries using whiteboard.md. No unsupported claim of mathematically guaranteed unique-human fairness.

## 5. Participant journeys
| Situation | Required behaviour |
| --- | --- |
| Event scheduled | Show published start/end and entry rules; entry button waits for server phase |
| Valid entry | Commit first, return one receipt, explain that the tab may close |
| Duplicate click or tab | Return the same domain entry; never create another chance |
| Lost response | Check /me state; replay the same mutation key when appropriate |
| Offline before acceptance | Explain entry was not confirmed; do not fabricate a receipt |
| Offline after acceptance | Keep receipt visible and recover server state on reconnect |
| Draw pending | Show saved entry; rank remains undisclosed until published |
| Offer | Show server-corrected deadline and confirmation action |
| Confirmation | Lock/check valid offer and commit ownership; show backend result |
| Expired offer | Explain expiry and seat release; never revive locally |
| Waitlist | Show published rank and explain promotion from original ordering |
| Cancelled drop | Show audited reason; no new entries or offers |
| Throttled user | Preserve accepted state; show backoff and a recovery action |
| Shared Wi-Fi | Independent eligible identities retain independent entries |

## 6. Functional acceptance
FR-01: A real participant can finish login -> discovery -> entry -> receipt -> draw outcome -> confirmation -> ticket.
FR-02: Profile/history/logout use persisted backend data.
FR-03: One eligible identity creates at most one entry and has at most one current seat ownership per drop.
FR-04: Active reservations plus confirmed seats never exceed configured capacity.
FR-05: Deadline races, reconnects, worker restarts and retries preserve consistent state.
FR-06: Organizers operate only authorized drops through real API endpoints.
FR-07: Every visible action works or explicitly states a real unavailable condition.
FR-08: Proof verification reproduces the ranking and commitment checks after publication.
FR-09: Attack reports use actual delivered traffic and database outcomes.
FR-10: Shared-identity and shared-network tests are distinct.
FR-11: Private identities/credentials do not appear in public manifests or exports.
FR-12: Lab/test fixtures cannot run in the normal product profile.
FR-13: Cancellation and lifecycle changes are audited and reflected across client refreshes.

## 7. Nonfunctional requirements
Integrity and ownership are mandatory; performance targets are evaluated on recorded hardware. First benchmark target: p95 successful authenticated reads/entry writes under 1 second at a declared sustainable workload. This is a goal, not an existing measurement or a universal SLA. Separate draw computation, network overhead and throttled response timing.

Use bounded connections, request bodies, worker batches, lab jobs, retries, timeouts, result pagination and polling. Acknowledged domain state must survive API/Redis/worker process restarts through PostgreSQL. DB or host data loss requires backups/recovery; it is not solved by process restart tests.

User experience targets: 360px through desktop, keyboard operability, meaningful focus/labels, reduced-motion support, clear errors and no per-second polling across all participants.

## 8. Demonstration evidence
Use matched populations/settings against a demo-only safe FCFS comparator. Both enforce uniqueness and inventory, so policy changes are isolated. Historical unprotected "naive-fcfs" supplied runs are labelled separately and not conflated with the controlled comparator.

Record initial-offer rates per accepted identity, attempted-to-accepted admission rates, bot actor/credential share, confirmed outcomes, p95/p99, expected 429s, unexpected errors, duplicate ownership, inventory invariant, achieved load, generator saturation and hardware. Repeat randomized trials and report sample sizes/intervals. Jain index across quartiles is descriptive, not a fairness certificate.

Preserve the supplied summary as unreproduced evidence. Do not extrapolate 400 participants/40 seats/one trial into a 50k-concurrency guarantee.

## 9. Scope priorities
P0: shared foundation, durable auth, eligibility, unique entry, closure, draw, reservation, confirmation, expiry, recovery, full participant journey.
P1: organizer workflows, profile/history, proof UI, lab controls/reports, controlled comparator, browser/concurrency evidence.
P2: notification inbox, external independent randomness, transactional real payments, stronger identity verification, organizer invitations/self-service and optional import tools.

P2 is a roadmap, not a hidden unfinished part of P0. The shipping demo must clearly disclose simulated checkout and invitation-based identity. Do not replace P0 correctness with decorative features.

## 10. Out of scope for the initial build
Referral-based extra entries, paid priority, reverse auctions, ticket resale, invitation trading, public load generators, broad web scraping, email/SMS dependency for core operation, blockchain infrastructure and ML-based draw weighting.

Product completeness within this scope does not imply readiness to collect real customer money or defend against volumetric internet DDoS.


## 11. Submission package and definition of done

| Deliverable | Evidence required | Accountable owner |
| --- | --- | --- |
| FairDrop participant website | Real sign-in, entry, receipt, outcome, confirmation, ticket and refresh | P3 with P1/P2 |
| Organizer console | Owned drafts, grants, locked publication, permitted cancellation, audit/inventory | P3 with P1/P2 |
| Allocation engine | Same fixed ranking, unique entries/seats, expiry/promotion and restart checks | P1 |
| Session/abuse controls | CSRF/ownership, shared limiter across two replicas, shared-IP and outage tests | P2 |
| Fairness proof | Public pseudonymous proof, verified seed/manifest/rank/inclusion | P1 + P3 |
| Attack lab and analytics | Matched FCFS/LOTTERY real HTTP run with DB-audited report | P4 + P3 |
| Infrastructure and evidence | Fresh-checkout instructions, Docker setup, real test/load reports and limitations | P4 |
| Explainable handoff | Updated memory and whiteboard evidence; human review recorded only if performed | All four |

A complete hackathon core needs the participant flow, organizer draft/publish path, all ownership/deadline invariants, expiry/recovery, proof and at least one measured adversarial comparison. Optional experiments and broader scale claims can be deferred with an explicit status. A front end connected to fixtures alone is not complete. A test that did not run is not a pass.

Notifications use authenticated status views/polling in this scope; email delivery is optional. The ticket is a persisted registration receipt, not a scannable admission-security system. Confirming a reservation is simulated checkout with no payment provider. No transfer, resale or paid priority is implied.

## 12. Metrics definitions

Let A_h/A_b be accepted eligible human/bot-labeled identities in the frozen manifest; O_h/O_b their **initial** offers, before expiry/promotion; T_h/T_b identities attempting entry. Labels come from the harness, never production rank logic. Identity is an account; actor may control several accounts. Count each account once, not every session/request.

| Metric | Definition and interpretation |
| --- | --- |
| Human admission | A_h / T_h; report bot admission A_b / T_b separately |
| Initial cohort selection rate | O_h / A_h or O_b / A_b |
| Bot Advantage Ratio | (O_b / A_b) / (O_h / A_h); around 1 over repeated trials is consistent with equal accepted-identity treatment |
| Bot initial-offer share | O_b / (O_h + O_b) |
| Bot identity share | A_b / (A_h + A_b); disclose actor-to-credential mapping |
| Final human success | Confirmed human identities / A_h; separately affected by confirmation behavior and outages |
| Latency-group rates | Initial offers / accepted identities in each measured latency quartile |
| Jain index | `(sum(rates)^2) / (4 * sum(rate^2))` across four nonempty latency quartiles; descriptive only |
| Latency correlation | Pearson r between measured pre-entry latency and binary initial-offer indicator for accepted identities; also measure arrival-time relation separately |
| Inventory | OFFERED + CONFIRMED <= capacity at every sampled/asserted transition; EXPIRED is excluded |
| Performance | Successful-request p50/p95/p99, achieved RPS, endpoint/status breakdown, expected 429s and unexpected 5xx |
| Availability/recovery | Unaccepted attempted identities, missed confirmations, outage/recovery time and explicit failures |

Undefined denominator, empty quartile or constant correlation input returns null with a reason. When human offer rate is zero and bot rate positive, report an undefined/infinite ratio label and counts; do not serialize Infinity as JSON or substitute zero. When all group rates are zero, Jain is undefined. Keep initial selection, promotions and final confirmation outcomes separate. Do not demand bot wins <5% or Jain >.95 as universal pass gates. Run repeated trials, show sample size and binomial rate intervals; P4 records the interval method. Integrity and deterministic request-independence are test gates; single-draw fluctuation is not a correctness failure.

The strong deterministic check keeps the same public entry IDs, manifest and seed in a private test fixture and changes arrival/retry patterns: every rank must match. Recreating entries with new random IDs does not represent the same fixture.
