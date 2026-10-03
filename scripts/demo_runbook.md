# FairDrop demo runbook

Start the isolated demo stack using README.md and run the Docker preflight.
Container startup still needs verification on a host with a running daemon;
local process/browser acceptance evidence is in INTEGRATION_REPORT.md.

1. Provision organizer/participant codes offline. Sign in, copy the participant's
   public account ID from their profile, create a draft and grant that invitation.
2. Publish before the entry start. Show that a participant saves one receipt and
   that refresh/two devices recover the same saved entry.
3. Show an offered seat, confirm it, then refresh its receipt. Show an unconfirmed
   offer expiring and the ordinary worker promoting the next persisted rank.
4. Download the public lottery proof and run `python -m app.audit.verifier` to
   reproduce commitments and ranking. Explain admitted-pool/personhood/operator
   limitations.
5. Run a small `policy_compare` experiment in the lab. Display each policy's
   admitted identities, initial offers and integrity audit separately. Use multiple
   independent trials for trial-level intervals; one trial has no interval.
6. Export the measured report. Show achieved versus target HTTP RPS, dropped
   iterations, latency, errors, provenance and null uninstrumented generator peaks.

The dedicated runner creates matched synthetic credentials/grants and fresh
policy drops for every trial. It uses real HTTP admission, the same limiter and
the same authoritative seat model. It never directly inserts winners.

For a CLI smoke run, put the offline-provisioned organizer code in a private JSON
file `{ "access_code": "..." }` and run:

```sh
python3 scripts/http_smoke.py --credential-file private/organizer.json --output reports/local-smoke.json
```

Use the existing allowlisted `failure_injection.ps1` only against the isolated
`fairdrop-demo` project. The Redis/worker-failure and shared-source-IP k6 scenarios
require explicit host/controller confirmation and a private fixture; the unattended
API rejects them. Never forge forwarding headers as a shared-IP simulation.
Stopped and failed runs retain partial artifacts; an interrupted job is failed
on runner restart. Show only measured outcomes and the tested scale.
