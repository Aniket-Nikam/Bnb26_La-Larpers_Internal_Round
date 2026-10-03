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
