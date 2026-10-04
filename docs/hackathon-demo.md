# FairDrop judge demo

FairDrop is not a faster ticket queue. It changes the unit of competition from HTTP requests to eligible identities, then makes the result independently checkable.

## Five-minute story

### 0:00 to 0:35 | The unfair rush

Open **Fairness** and move the request-volume slider. Explain that two automated identities can dominate a speed-based sale by sending many requests, while FairDrop still admits only two entries for those identities.

Say: “Rate limits protect availability. Identity-bound entries protect allocation. We deliberately keep those two jobs separate.”

### 0:35 to 1:25 | A participant enters once

1. Open **Discovery** and choose a published drop.
2. Create or sign in to a participant account. Registration verifies one face per account.
3. Select **Enter fair draw**.
4. Refresh the page and show that the same durable receipt returns.
5. Copy the public entry ID and point out that retrying never creates another entry or improves rank.

### 1:25 to 2:35 | The organizer allocates safely

1. Open **Organizer** and select the prepared drop.
2. Show capacity, accepted entries, active offers, confirmed seats, free seats, and the integrity badge.
3. Close entry and start the draw.
4. Explain the lifecycle: freeze the manifest, reveal the committed seed, rank every frozen entry, reserve seats atomically, then promote the next original rank after expiry.

### 2:35 to 3:20 | The winner confirms

1. Return to the offered participant.
2. Show the server-derived confirmation countdown.
3. Confirm the offer.
4. Refresh and show the confirmed receipt is still present.

### 3:20 to 4:10 | Anyone can verify the draw

1. Open **Draw proof**.
2. Download the proof bundle.
3. Point out the frozen pseudonymous manifest, seed commitment, disclosed ranking algorithm, and published ranks.
4. Run the independent verifier if a terminal is part of the presentation.

### 4:10 to 5:00 | Prove resistance under attack

1. Open **Attack lab** in the isolated demo profile.
2. Select a prepared measured run, or start a small normal or retry-flood scenario.
3. Show achieved RPS, successful-request p95, dropped iterations, human and automated cohort offer rates, and inventory integrity.
4. Export the evidence JSON.

Say: “This report distinguishes requested traffic from delivered traffic, preserves limitations, and never claims a 50,000-user benchmark we did not run.”

## Demo data to prepare

- One published lottery drop with 3 seats and 8 to 12 participants.
- One participant already entered, one offered, and one confirmed.
- One normal lab report and one retry-flood or policy-comparison report.
- Organizer and participant credentials stored only in the repository's ignored private directory.
- A clean reset checkpoint using the documented demo reset script.

## Judge questions

**Can bots still create many accounts?**  
Registration checks for duplicate facial embeddings, while FairDrop enforces one entry per account and rate limits abuse. Facial similarity is an admission control, not proof of personhood, and the presentation must not claim universal Sybil prevention.

**Does Redis decide who gets a ticket?**  
No. Redis protects the edge and sessions. PostgreSQL transactions, row locks, and constraints own entries, offers, confirmations, inventory, and audit history.

**Can the organizer change the draw after seeing entrants?**  
The manifest freezes when entry closes. The committed seed, disclosed algorithm, and public proof let an independent verifier reproduce ranking.

**What happens after a refresh or network failure?**  
The durable session and idempotent entry endpoint recover the same receipt. Confirmation uses the server deadline, and duplicate requests do not create duplicate ownership.

**Did you actually test the claims?**  
Use the checked-in integration report and measured JSON artifacts. State the tested workload honestly and separate measured facts from the illustrative fairness explainer.

## Presentation fallback

If the live attack worker is unavailable, do not improvise numbers. Open a checked-in measured report, explain its exact source checkpoint and limitations, then demonstrate the participant receipt and proof flow live. The core allocation path does not depend on the optional lab capability.
