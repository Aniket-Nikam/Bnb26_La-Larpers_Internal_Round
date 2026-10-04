# 500 seats / 50,000 identities — local scale-test record

**Date:** 2026-10-04  
**Status:** Failed / inconclusive — not presentation evidence of successful 50,000-identity capacity.

## Requested workload

| Setting | Value |
| --- | ---: |
| Scenario | `normal` |
| Human synthetic identities | 40,000 |
| Automated synthetic identities | 10,000 |
| Seats | 500 |
| Requested HTTP rate | 2,000 RPS |
| Traffic duration | 41 seconds |
| Retries per identity | 0 |
| Trials | 1 |
| Lab run ID | `967c4bad-7c39-42de-89ba-00dc38eb9c86` |

## Direct observations

1. The Attack Lab accepted the job and changed its state from `QUEUED` to `RUNNING`.
2. During the active run, refreshing the organizer page returned the public shell with: `Failed to execute 'json' on 'Response': Unexpected end of JSON input`.
3. An immediate health check could not connect to `127.0.0.1:8010`; the FairDrop API was no longer listening on that port.
4. As a result, no terminal lab report, achieved RPS, accepted-entry count, allocation result, or integrity audit was available.

## Interpretation

This is a valid negative result: this local launch configuration did **not** sustain the requested workload. It must not be presented as proof that FairDrop handled 50,000 people or safely allocated 500 seats.

There is also a request-budget limitation in the current lab route. Its guard computes
`target_rps × duration × trials × 3`; with the maximum 250,000-request budget, this
41-second run can schedule roughly 27,000 complete normal-entry iterations, not all
50,000 distinct configured identities. The lab UI correctly exposes achieved traffic
separately, but this formula must be corrected before a full-population run can be
claimed.

## Required before a presentation claim

1. Fix the request-budget calculation so that the configured HTTP RPS corresponds to
   the actual k6 request budget.
2. Run the lab in the supported containerized deployment with PostgreSQL, Redis, API,
   allocation worker, and lab worker available throughout the run.
3. Capture a terminal report that shows all of the following:
   - 50,000 attempted and accepted unique identities;
   - exactly 500 or fewer offers/confirmed seats;
   - zero oversold seats and zero duplicate active owners;
   - achieved RPS, p95 latency, dropped iterations, and unexpected 5xx responses;
   - the bot-to-human offer-rate comparison and verified audit.

Until then, use the existing smaller completed runs only as bounded functional and
fairness demonstrations, not as 50,000-person scale evidence.
