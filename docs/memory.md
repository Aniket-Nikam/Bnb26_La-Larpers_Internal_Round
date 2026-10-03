# FairDrop — memory template (not an active progress log)

Build pack: FairDrop merged specification v1.0 · 2026-10-03.
This file records no completed code, test, integration or human review.
Do not rename/copy it to memory.md during initial documentation preparation.

## Activation and ownership

When the first actual implementation edit begins, P1 copies this file to memory.md,
changes the heading to "FairDrop — implementation memory", removes these activation
instructions, fills observed values, and commits it with the implementation.
Missing facts remain UNKNOWN / NOT RUN / BLOCKED, never guessed. Creating the
specification package does not count as beginning application coding.

P1 owns active memory until bootstrap handoff. P4 then becomes the only writer of
integrated memory. Each member updates their own progress/person-N.md, created at
coding start. Integrated status requires a merged commit and actual checks; a
feature branch's success is recorded separately. Update before switching chats/AI
tools, at phase gates, and before handoff. Do not store secrets or raw terminal logs.

Everything below is a blank schema. Replace placeholders only with observed facts.

## Session snapshot

- Updated UTC: <timestamp or UNKNOWN>
- Central writer: <P1 during bootstrap; P4 after handoff>
- Repository / integration branch: <path / branch>
- Integrated commit: <actual hash or UNKNOWN>
- Working tree: <clean or exact uncommitted paths>
- Current phase: <phase number and active behavior>
- Bootstrap handoff: <commit / recipients / date or NOT DONE>
- App status: <what actually runs and what does not>
- Contract / algorithm / dependency locks: <actual versions/paths or NOT CREATED>
- Environment: <demo/test/normal; hardware/services; no secret values>

## Member work and current files

| Member | Branch / actual head | Active task | Files currently edited | Files/behavior verified on branch | Merged and verified | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| P1 | <UNKNOWN> | <task> | <exact paths> | <behavior + commit/check> | <evidence or NOT INTEGRATED> | <action> |
| P2 | <UNKNOWN> | <task> | <exact paths> | <behavior + commit/check> | <evidence or NOT INTEGRATED> | <action> |
| P3 | <UNKNOWN> | <task> | <exact paths> | <behavior + commit/check> | <evidence or NOT INTEGRATED> | <action> |
| P4 | <UNKNOWN> | <task> | <exact paths> | <behavior + commit/check> | <evidence or NOT INTEGRATED> | <action> |

If a branch head is stale, mark STALE and include the last observation time. Do not
label a whole file complete merely because a handler exists. Name behavior,
remaining paths/states and checks.

## File-level completion register

| Exact file/path | Owner | Status | Implemented behavior | Remaining work | Commit + check evidence |
| --- | --- | --- | --- | --- | --- |
| <path> | <member> | <NOT STARTED / IN PROGRESS / BLOCKED / VERIFIED ON BRANCH / INTEGRATED AND VERIFIED> | <facts> | <facts> | <actual evidence or NOT RUN> |

## Phase gates

| Phase | Status | Integrated commit | Actual gate evidence / blocker |
| --- | --- | --- | --- |
| 0 Foundation | <NOT VERIFIED> | <UNKNOWN> | <actual result> |
| 1 Auth/public shell | <NOT VERIFIED> | <UNKNOWN> | <actual result> |
| 2 Durable entry | <NOT VERIFIED> | <UNKNOWN> | <actual result> |
| 3 Draw/confirmation | <NOT VERIFIED> | <UNKNOWN> | <actual result> |
| 4 Expiry/recovery | <NOT VERIFIED> | <UNKNOWN> | <actual result> |
| 5 Complete UI | <NOT VERIFIED> | <UNKNOWN> | <actual result> |
| 6 Attack lab | <NOT VERIFIED> | <UNKNOWN> | <actual result> |
| 7 Capacity/integration | <NOT VERIFIED> | <UNKNOWN> | <actual result> |
| 8 Demo/whiteboard | <NOT VERIFIED> | <UNKNOWN> | <actual result; human review separate> |

## Checks actually executed

| UTC time / commit | Command | Scope / environment | Result | Evidence file or failure/blocker |
| --- | --- | --- | --- | --- |
| <actual value> | <exact command> | <real DB/replicas/browser/hardware> | <PASS / FAIL / NOT RUN> | <path and short result> |

Record concurrency, security, browser, proof and recovery checks independently.
A fixture/SQLite-only test does not establish PostgreSQL race safety. Never turn
an expected pass or a supplied summary into an executed result.

## Measured run register

| Run/report path | Commit/profile/hardware | Target vs delivered workload | Integrity/admission/selection result | Limits/source |
| --- | --- | --- | --- | --- |
| <path> | <actual> | <identities/RPS/connections/dropped iterations> | <counts> | <measured or supplied_unreproduced; caveats> |

Distinguish unique population, virtual users, connections, in-flight requests and
RPS. Separate initial offers, promotions and confirmations; do not fill missing
metrics with zero.

## Contract, migration and cross-owner changes

| Change | Owner | Affected paths/consumers | Migration/contract version | Handoff/integration status |
| --- | --- | --- | --- | --- |
| <concrete change> | <member> | <paths> | <actual version> | <pending/merged + evidence> |

## Blockers and next actions

| Blocker | Impact | Responsible owner | Next concrete action | Dependency/check |
| --- | --- | --- | --- | --- |
| <blocker> | <behavior affected> | <member> | <action> | <needed evidence> |

## Decisions and whiteboard evidence

| WB ID | Implemented choice / reason | Commit/path | Actual evidence | Human review |
| --- | --- | --- | --- | --- |
| <WB-xx> | <facts> | <path/hash> | <check/report> | <PENDING unless a human supplied the record> |

## Next-session instructions

1. Read rules.md, this memory, your own progress and the relevant phase/API section.
2. Check current branch/head and uncommitted files; verify this log's known facts.
3. Inspect only code relevant to <next concrete task>; preserve other owners' work.
4. Complete <behavior> and run <required meaningful checks>.
5. Update your progress, send cross-owner handoffs, and have the central writer
   record only merged and verified outcomes.

## Per-member progress record schema

Each progress/person-N.md contains: updated UTC; member/branch/head; assigned task;
exact in-progress paths; implemented behavior; completed files with evidence;
actual commands/results; failed or not-run checks; remaining work; blockers;
cross-owner handoff; next action. This prevents four writers colliding in memory.
