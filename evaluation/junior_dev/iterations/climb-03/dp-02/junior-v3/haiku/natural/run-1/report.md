## Review of dp-02 (junior-v3, author haiku, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Added a short 'what this is and how it works' summary before the terms.
- Defined the envelope, claim, delivery limit and operator in the terms section, and marked that the 7-day buffer is SDK behaviour not verified as enforced.
- Replaced the R1 to R11 codes and the Part A/B/C headings with plain numbered steps that stand alone.
- Live step 7: offsets commit only up to the last fully committed micro-batch, so a dropped duplicate in the same partition cannot hide a pending first copy.
- Live step 8: named the version as the KV record's revision, and stated that a slow consumer's failed commit discards its result and that duplicate writes are identical.
- Live step 9: stated that a copy after W can create a second row for the same event_id in another day, which breaks first-copy-wins, and that replay with an 8-day lookback cannot detect it. Linked this to the window-size question.
- Replay step 4: stated the lookback margin and the live versus replay tie-break in plain words.
- Replay step 8: the live-write check now runs again immediately before the swap, and the remaining non-atomic gap is stated.
- Added a failure-handling table covering collector, validation, client timeouts, KV, warehouse, sink, replay and post-swap writes.
- Moved all unresolved points into one open-questions list. Added KV product and owner, SDK enforcement, finding stale claims, and operator and sign-off, which were previously unstated.
- Kept bot-traffic handling open and unchosen, as the brief requires.
- Replay intro and step 8: replaced 'does not touch KV' with 'never writes to KV'. Step 8 is now a read-only KV check for pending claims with first_received_at in D, run again before the swap (Q9).
- Live step 5: stated that the claim is written before the event is buffered, so pending claims cover in-flight micro-batches (Q9).
- Live step 8: spelled out what the takeover does with each event on re-read, and that offsets stop at the first claim it cannot take over (Q10).
- Live step 7: stated that a committed claim stays until TTL W expires (Q11).
- Failure table: added the row for a consumer crash after the warehouse write, and the row for a replay whose live-write check cannot read KV (Q9, Q11).
- Replay step 1 gate: added the wait for the collector write timeout T after close, so late in-flight requests can finish writing (Q12).
- Added open questions 10 (collector write timeout T) and 11 (replay timing). Extended open question 4 with the KV query for pending claims.
- Simplified for a newcomer: merged the source-of-truth term into the raw archive term, moved the 'Delivery limit' and 'Operator' terms to one line each, removed the duplicated late-copy explanation from the replay section, and made the close gate and monitoring list shorter.
- Replay intro now states that replay never writes to events_raw, KV or live offsets.
- Merged the old validate step into the receive step, so the live path has one step for receive, stamp and check.
- Merged the replay pin-versions step into the replay gate step, so the replay gate, lock and version pinning are one step.
- Merged the replay read-archive and enrich steps into their neighbours, and combined the old enrich and stage steps, reducing replay from ten steps to eight.
- Moved the close gate, monitoring and retention notes out of their own section into a short checks block after the failure table, since they describe failure detection.
- Replaced cross-references such as 'open question 8', 'steps 4 to 6', 'replay step 1' and 'step 8' with named references or self-contained wording, so each step stands alone.
- Cut the duplicated 'at 02:00 UTC after close' and 'live consumer' repetitions across the summary, live steps and failure table, and shortened the terms to one line each.
- Kept the intent unchanged: bot-traffic handling stays open, the dedup window stays W = 8 days, all replay checks and the live-write check stay, and no new mechanism was added.
- Open questions kept as a single list; the duplicate 'enforcement of the 7-day SDK buffer' item was kept separate from the window-size item rather than merged, so no open question was dropped.

### Holes
- Q7: Who triggers a replay of day D and why would they (what problems are being fixed)? Who is the 'operator' and how do they sign off the diff in R7? (author: The brief says an operator rebuilds one closed day, usually after an enrichment bug such as a geo-IP or user-agent fix is found. The brief does not name the operator, and it does not say who signs off a removal above the threshold, or how sign-off is recorded. These are open questions 6 and 9. The plan now defines operator as the person who starts a replay.)
