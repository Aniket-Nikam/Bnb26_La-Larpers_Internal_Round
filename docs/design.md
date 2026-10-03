# FairDrop — visual and interaction design

Build pack: FairDrop merged specification v1.0 · 2026-10-03.
Status: specification only; no code, benchmark, completed phase or human review is claimed.
The interface is a complete ticket/registration product with a separate organizer workspace. This document specifies intended design, not screenshots of an implemented website.

## 1. Visual direction
Calm, confident and distinctive. A receipt/ticket motif connects participation, proof and ownership. Public pages feel like an event platform; organizer screens feel like an operational console. They share tokens/components/navigation conventions.

Primary copy: "A fair chance. One saved entry."
Supporting copy: "Enter during the window. Selection happens after it closes."
Use restrained colour, crisp type, purposeful whitespace and clear state labels. Avoid fake live activity, overloaded hero cards, neon gradients, rotating slogans or claims such as "100% bot-proof."

## 2. Design tokens
| Token | Value | Use |
| --- | --- | --- |
| canvas | #F7F8FA | Application background |
| surface | #FFFFFF | Content panels/dialogs |
| ink | #172033 | Main text |
| muted | #526075 | Secondary text |
| border | #DCE2EB | Dividers/inputs |
| primary | #2548C8 | Main actions/links |
| primary-hover | #1D38A0 | Hover state |
| success | #176449 | Confirmed state |
| success-surface | #EAF5EF | Success background |
| warning | #805600 | Pending/expiry warning text |
| warning-surface | #FFF3D6 | Warning background |
| danger | #B32632 | Errors/destructive state |
| danger-surface | #FCEDEF | Error background |
| focus | #2548C8 | Visible focus outline |

Check actual combinations for WCAG AA during implementation; token listing alone is not a contrast audit. Pair colour with icons/text. Data chart series: cobalt, teal, amber, violet, with direct labels and differing marks.

Typography: self-hosted Inter (or local/system sans fallback) for interface; optional self-hosted IBM Plex Mono for short receipt IDs, timestamps and technical details. Avoid loading font/CDN resources from the critical login/entry path. Body 16px/1.5, compact labels 14px/1.4, mobile form controls at least 16px, H1 40-56px desktop/32px mobile, H2 24-32px. Use tabular numbers for metrics/timers, not whole paragraphs.

Spacing scale: 4, 8, 12, 16, 24, 32, 48, 64px. Inputs/buttons roughly 44px minimum effective touch target. Card radius 12px; buttons/inputs 8px; restrained shadow only for overlays/floating navigation. Container max-width 1200px; participant status width around 720px. Use 12-column desktop/stacked mobile composition, not fixed-width screenshots.

## 3. Routes and screen inventory
| Route | Screen | Primary action/data |
| --- | --- | --- |
| / | Landing | Browse drops |
| /drops | Discovery | Search/filter paginated real drops |
| /drops/:id | Drop detail | Sign in, enter or inspect saved state |
| /sign-in | Invitation login | Continue to preserved destination |
| /my-entries | Participant history | Open receipt/current state |
| /account | Profile/session settings | Save name/timezone; logout |
| /entries/:id | Receipt/current ticket | Confirm offer or inspect status |
| /drops/:id/verify | Proof verifier | Verify commitments/ranking/inclusion |
| /organizer | Owned-drop overview | Create or inspect a drop |
| /organizer/drops/new | Draft form | Save draft |
| /organizer/drops/:id | Control workspace | Publish/manage permitted transitions |
| /organizer/lab | Attack laboratory | Start bounded scenario |
| /organizer/lab/:runId | Run report | Compare/export measured result |
| fallback | Not-found/forbidden | Safe route back |

Frontend route protection improves navigation; API role/ownership checks remain mandatory.

## 4. Public landing/detail
A compact header: FairDrop brand, Explore, How it works, Verify, My Entries/account. Organizer access appears by authorized role. Mobile menu has accessible focus handling.

Hero states the promise, one primary Explore action and a three-step explanation: verify invitation, enter once, receive outcome. Featured drops come from the API. No stock numbers imply real activity.

Drop cards show category, title, schedule, organizer, entry phase and capacity. Detail page prioritizes event facts, entry window and rules. Organizers may use safely managed event media later; the baseline must look intentional without generated art. Do not obscure policy behind decorative illustrations.

## 5. Participant receipt/status
Use a ticket panel: title, status label, short public receipt ID, acceptance time, current instruction and proof link. Visual dotted separators/perforation are decoration; never convey status by them alone.

| Backend state | Copy | Action |
| --- | --- | --- |
| No entry, SCHEDULED | "Entry opens at …" | Review rules |
| No entry, OPEN and eligible | "One eligible identity receives one entry." | Enter drop |
| Entry ENTERED | "Your entry is saved. You can close this tab." | View receipt |
| CLOSED/DRAWING | "Selection is being prepared." | Optional refresh |
| WAITLISTED | "You are on the ranked waitlist." | See rank/promotion explanation |
| OFFERED | "A seat is reserved for you until …" | Confirm reservation |
| CONFIRMED | "Your reservation is confirmed." | View/download receipt |
| EXPIRED | "The confirmation window ended." | Explain seat release |
| CANCELLED | "The organizer cancelled this drop." | Show audited reason |
| Not eligible | "An invitation for this drop is required." | Explain organizer access |
| Connection lost before success | "We could not confirm your entry yet." | Check state/retry |
| Offline with accepted receipt | "Your saved entry remains; live updates are unavailable." | Reconnect |

Do not call WAITLISTED a guaranteed future ticket. Do not show invented queue position before draw publication. Rank is ordering, not an exact waiting-time estimate.

## 6. Organizer experience
Use a left navigation on desktop and compact drawer on mobile. Drop control presents facts and state-dependent actions. Invalid actions are disabled with the reason visible.

Inventory visual: capacity slots grouped by free, offered and confirmed; text counts accompany colour. Current ownership numbers derive from API metrics. Audit history shows meaningful transitions and safe actors, paginated. Do not render 50k rows or 500 individual tiny seat labels as the only explanation.

Attack lab has two zones: bounded scenario configuration and a run/report view. Controls: scenario, legitimate/bot actor counts, requests per second, burst/duration, retry behaviour, policy comparison. Clearly display the configured demo target; never editable arbitrary URL.

Reports show legitimate admission success and selection rates together, bot identity/actor share, capacity/duplicate invariant, p95/p99, achieved load and generator limits. Compare groups on shared axes. A loaded historical report shows source, timestamp, scale and "Supplied; not independently reproduced" label. Running charts cannot generate random points while waiting.

## 7. Forms and interactive states
Draft forms validate schedule/capacity and explain which settings lock on publication. Descriptive edit and policy edit are distinct. Profile forms do not expose roles/grants. Sign-in accepts an access credential but does not echo it into URLs, logs or persistent client storage.

Explicit states: idle, loading, empty, saving, uncertain-result, success, validation error, offline, throttled, service degraded, forbidden and not found. Skeletons preserve layout; no indefinite spinner without explanation.

Use durable non-secret idempotency keys for pending mutations. If a write times out, inspect /me before issuing a new domain operation. Focus moves to meaningful error/success feedback; use appropriate live regions without announcing every countdown tick.

## 8. Time and network
Use server_time to estimate display offset. Always include an absolute formatted deadline and timezone alongside a countdown. Countdown expiration refetches; it does not locally expire/confirm a seat. Resync on focus/reconnect.

Polling defaults to 10-20 seconds plus jitter while state can change, slows under errors, pauses in hidden tabs and stops when terminal. Small demo profile can explicitly use shorter intervals; large load includes the actual configured polling. Do not rely on keeping an SSE/WebSocket connection alive to preserve ownership.

## 9. Accessibility and responsive checks
Native buttons/links, labelled fields, error descriptions, focus-visible styling, semantic headings and tables. Dialogs/drawers manage focus/escape. Icons have accompanying labels for key actions. Avoid colour-only charts; provide data summaries.

Review 360px, 768px and 1280px. Tables get responsive columns/scroll regions without whole-page overflow; forms stack; nav wraps or collapses. Touch targets do not overlap. Respect prefers-reduced-motion; transitions about 120-200ms and no constant motion.

## 10. Design completion
P3 verifies the real participant journey and organizer lab on the merged API. Every visible metric has a source or an explicit unavailable state. No placeholder cards/actions, silent mocks, fake winners or nonfunctional export buttons survive the completion gate.


## 11. Judge-facing comparison view

Use one overview with FCFS_DEMO and FairDrop side by side. Header includes run ID, source (measured or supplied/unreproduced), timestamp, commit, trials, capacity and accepted/attempted population. Cards show human admission, human initial-offer rate, bot advantage, integrity, p95 and achieved RPS. Jain and correlation are secondary descriptive charts, with sample sizes. Definitions follow prd.md; do not mix initial offers with sold/confirmed counts.

Chart 1: initial-offer rates by measured latency quartile with the same axes for both policies. Chart 2: human/bot identities versus initial offers, with actor-to-credential share disclosed. Traffic table uses actual redacted events/aggregate batches and stays bounded; do not render one UI row per request at load. Add plain text/data table equivalents. A null ratio shows "Not defined" with its reason and cohort counts. Throttling and service failures appear beside admission so fairness charts cannot hide exclusion.

Optional defense-profile selector appears only if the corresponding lab experiment is implemented. PoW/risk mode says "Admission experiment — accepted-entry ranking unchanged" and reports human friction. Offline weighted-policy historical results have a separate label and cannot become the production mode. Keep the default interface clean if those features are deferred.

## 12. Frontend route/API alignment

UI routes remain the paths listed above; API paths come from architecture.md. My Entries calls GET /api/v1/entries. An offer confirmation calls POST /api/v1/reservations/{reservation_id}/confirm. Organizer pages call /api/v1/admin, and lab pages /api/v1/admin/lab. The proof endpoint contains the manifest/ranking; do not invent a separate manifest route. Settings do not expose grant or role editing. No separate API specification or ad hoc client payload overrides these routes.

Final waitlist copy when the drop completes full: "All seats are confirmed. This drop is complete." An exhausted undersubscribed drop states actual confirmed count; it never invents a sellout. Pending rank and empty metrics have explicit displays. The normal app cannot show experimental lab controls to participants.
