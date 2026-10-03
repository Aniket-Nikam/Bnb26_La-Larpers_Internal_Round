# FairDrop measured HTTP workloads

These k6 scenarios call the normal cookie/session/CSRF API. They never insert
entries, winners, or reservations directly. The runner supplies a fixed target
origin and a private credential fixture; neither is accepted from the browser.

Private fixture shape (never commit a populated copy):

```json
{
  "drop_id": "uuid",
  "policy_drop_ids": {"fcfs_demo": "uuid", "lottery": "uuid"},
  "actors": [
    {
      "actor_id": "human-1",
      "cohort": "human",
      "credentials": [{"access_code": "secret-issued-by-P2"}]
    }
  ]
}
```

An actor may own multiple credential records. Reports count identity outcomes
once per credential and separately disclose the actor-to-credential mapping.
Provisioning is outside measured entry traffic.

`shared_ip` refuses to run unless the deployment confirms a controlled shared
source-network topology. It never sends a client-selected forwarding header.
`worker_restart` and `redis_failure` refuse to run unless the host-side,
allowlisted failure controller confirms injection. These safeguards prevent a
plain traffic run from being mislabeled as failure evidence.

## Integrated runner update

The dedicated `app.lab.worker` now consumes PostgreSQL LabRun jobs from the admin
API. It provisions fresh matched synthetic identities, grants and drops per trial,
executes the allowlisted k6 scripts and reconciles outcomes with the allocation
models and proof verifier. See README.md / INTEGRATION_REPORT.md for current setup.
The workload records redacted endpoint/status/latency/public-identity observations
in private artifacts. Arrival rates are calibrated for the expected HTTP requests
per healthy iteration; reports expose the actual achieved HTTP RPS. Public exports
separate policy outcomes and contain no raw codes, cookies or CSRF/session secrets.
