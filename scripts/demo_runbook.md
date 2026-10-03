# Five-minute FairDrop demo runbook

Status: integration checklist only. Do not rehearse or claim completion until
the preflight, real browser journey, authoritative DB audit, and measured report
all pass from a fresh checkout.

## Before the clock starts

1. Start the isolated `fairdrop-demo` Compose project and verify both health
   endpoints, two API replicas, worker, PostgreSQL, Redis, and runner.
2. Provision the matched human/bot actor mapping privately. Create equal-capacity
   FCFS_DEMO and LOTTERY drops with identical grants, limits, and prerecorded
   schedules. Ensure the FCFS hold covers entry plus comparison capture.
3. Run a small smoke comparison. Confirm `report.json` agrees with authoritative
   database counts and contains no credential/session/CSRF secret.
4. Keep larger saved reports visibly labelled with commit, hardware, delivered
   workload, dropped iterations, and limitations.

## Live sequence

1. **0:00–0:45 — FCFS pressure.** Show the early-bot schedule, start the bounded
   FCFS run, and explain that FCFS remains inventory-safe but rewards arrival.
2. **0:45–1:30 — Matched FairDrop.** Replay the same actors, credentials, request
   schedule, capacity, and limiter settings against LOTTERY. Compare accepted-
   identity initial-offer rates; do not compare request counts as lottery chances.
3. **1:30–2:20 — Durable one-entry behavior.** Enter with one participant, repeat
   with the same and a different operation key, refresh/reconnect, and recover the
   same receipt. A discarded response is reconciled with `GET /drops/{id}/me`.
4. **2:20–3:20 — Ownership transitions.** Confirm one active offer. Let another
   expire, show promotion from the persisted ranking, and point out the fixed
   capacity/duplicate-owner checks.
5. **3:20–4:20 — Verification.** Reproduce commitments/rank through the public
   proof verifier. State that reproducibility does not prove unique humanity or
   eliminate all operator trust.
6. **4:20–5:00 — Evidence and limits.** Show target versus delivered workload,
   dropped iterations, expected 4xx, unexpected 5xx, latency, generator headroom,
   identity versus actor share, and DB-audited integrity. State the tested scale
   and any outage/admission losses exactly.

## Abort conditions

Stop optional load experiments if integrity, auth, migration, browser, or report-
agreement gates are red. A small real run is preferable to an invented 50k claim.
Stopped/failed runs retain partial artifacts and must remain labelled partial.
