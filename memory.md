# FairDrop — implementation memory

Updated UTC: 2026-10-03. Central writer: P1 until bootstrap handoff, then P4.
Integration branch: main at 7eedd2f. Implementation branch: M1; not merged.
Phase: 0, shared foundation in progress. No integrated gate or human review claimed.

The template is currently misnamed docs/memory.md; docs/memory.template.md does not exist.
This active root memory records implementation; canonical specifications remain in docs/ per user.
Existing TypeScript ingress experiments are preserved, outside the default lottery runtime.
P2/P3 are not present in this checkout; P4 branch origin/codex/m4-infra-lab was inspected read-only.
Environment: Python 3.12 via uv; local PostgreSQL 18 available. Checks pending.

P1 creates the shared DTOs, models/migrations, imports and contract. Model fields are a
concrete proposed handoff; P2/P4 consumer acknowledgement remains pending.
P2 owns security after bootstrap; P4 owns lab and this central log after bootstrap.
Next: finish/check bootstrap, publish checkpoint, implement P1 domain and real-DB checks.

Bootstrap checks executed: locked uv install; migration upgrade/check on local
PostgreSQL 18 UTF-8, typed schema/examples export, TypeScript generation+compile,
pytest core 3 passed. Contract v1.0; migration b3194d72d2b4. Known warning: Starlette
httpx test adapter deprecation. No login/limiter/lab implementation or integration
claimed. Bootstrap handoff is contracts/HANDOFF.md; P2/P4 adoption pending.
Central memory ownership is handed to P4 at the bootstrap commit; P1 subsequently
updates progress/person-1.md only. Not merged to main. No human review performed.
