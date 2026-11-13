## Review of ms-02 (junior-v7, author haiku, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Summary: the publisher commits the handover before it publishes, and the summary now says what the message carries.
- Added a Terms section defining MailRelay, idempotency key, broker, monolith worker (old worker), publisher, route, route flag, claim and lease, handover, inbox and outcome outbox.
- Invariants: the single-owner rule now says the committed claim decides ownership, and the flag only decides which side tries first.
- Added a 'claim before publish' invariant. The publisher commits the handover before publishing, replacing the publish-then-commit order in step 6, so the monolith worker can never send a row the service also received. The reason is a flag flipped back during an outage.
- In-doubt rule is measured from first_claimed_at, not from the latest claim. Added first_claimed_at to the monolith and inbox schema, and published_at to the monolith schema.
- Step 2: the monolith worker's claim filter now depends on the flag, and the selection re-claims rows whose lease has expired.
- Step 6: handover commit, then publish, then published_at; a handed-off row without published_at is re-published each poll. Broker-down and publisher-crash failure lines rewritten to match.
- Step 5: states that status stays pending while a row is handed off.
- Rollback step 2: the publisher keeps publishing rows it already handed over, whatever the flag says.
- Step 6: the 7-day republish cap pages on-call. Step 7 reconciliation reports mismatches only, so the page is stated in one place.
- Step 9 and step 10: the order_confirmed bake is stated as at least 3 days, and password_reset starts at least 3 days after order_confirmed passes its gate.
- Open questions: added question 8 (source of the backlog-age alert). Questions 1 to 7 are kept unchanged, with a note added to question 7.
- Summary: the outcome is reported on notifications.outcome.v1 (named, per Q9).
- Terms, Broker: added the three topic names and what each carries (per Q9).
- Step 2, claim flow: the claim query now checks next_attempt_at, and a retryable failure keeps route = 'monolith' (per Q10).
- Schema changes: added shadow_published_at and render_hash on the monolith table, used by step 4 (per Q13).
- Step 4: the shadow publisher selects rows by shadow_published_at and created_at after deploy; the real monolith sending is unchanged; the monolith records render_hash; hash comparison moved to open question 9 (per Q13).
- Step 5: named the outcome topic, the outcome publisher's relay and retry, and the rule that events for non-service rows are not applied and are logged for reconciliation (per Q12).
- Step 6, publisher: publish target named as notifications.v1 (per Q9).
- Step 6, service worker: each row is sent and written on its own, and the MailRelay timeout must be shorter than the lease (per Q11).
- Step 7, reconciliation: added hourly cadence, what is compared, the Platform team as owner of mismatch reports, and events for non-service rows (per Q15).
- Rollback steps 2 and 3: the one-minute window covers new route-NULL rows only; a handed-off batch not yet published stays on the service (per Q14).
- Open questions: added 9 (dry-run hash comparison) and 10 (MailRelay send timeout and service batch size), both unknown in the brief.
- Cut: the summary is now three sentences. The earlier summary's invariant list, and its 'hands each row to the broker' and 'three layers' detail, were moved or merged into the Invariants and the moved-type flow.
- Merged: the cutover mechanics that steps 6, 8 and 10 each repeated are now one 'Moved-type flow' section. Steps 8 and 10 point to it instead of restating it.
- Merged: the separate failure lists in steps 6 and the claim flow were combined into one 'What happens when things fail' table. Each rollout step states its own failure handling in one line that refers to the table or to its own text.
- Moved: the column lists, which appeared in the summary, the invariants and steps 2 and 4, now appear once, under Data.
- Separated: how the system runs (Terms, Invariants, Data, Moved-type flow, failure table) is now apart from how it rolls out (Rollout steps, Rollback, Open questions).
- Added terms: MailRelay, idempotency key, broker, ack, lease, first claim, in-doubt, handover, route, route flag, claim, outcome outbox, terminal, idempotent, republish, reconciliation, p99, NTP, and ON CONFLICT DO NOTHING. Each is defined in one plain line.
- Added: a 'How it works today' section, so a reader knows the current behaviour before the change. It holds the current worker, the known problems and the owner, all taken from the overview.
- Clarified: 'inactive' publisher mode now means it runs but publishes nothing. The service claim now covers expired 'sending' leases. A service retry sets status back to 'queued'. These follow the answers to the junior's questions, and the first version left them implicit.
- Clarified: republish runs until the row is 7 days old, counted from handed_off_at. The first version did not say what the 7 days were measured from.
- Clarified: the step 2 claim filter, the route-NULL flag rule and the 'publisher never claims monolith rows' rule are stated once, under Invariants.
- Added: step 7 says the next type does not move until the soak gate passes. This follows from the gate. The brief does not state it explicitly.
- Removed: all numbered references to open questions and to other rules, so no reader has to look up a code. Each open item is named where it applies.
- Kept: every stated fact from the brief and the first version. That includes volumes per type, the 3-day bake, the p99 gate and the 60 s target, the 10 s flag propagation, the 1-minute rollback effect, the 30 s broker redelivery, the 24-hour MailRelay window, the 5 s poll and 50-row batch, the 30 days of retention, the 30 duplicate emails a week, the 7-day decommission, and the rule that the old worker stays deployable.
- Added to open questions: the p99 gate's sample size is undefined; the render-error decision is not yet made for the service worker; the payload decision must come before step 10.
- Decisions from the junior's answers are kept: the handover commits before publish (A2), the flag decides which side tries first and the claim decides ownership (A6), retries keep route monolith (A10), each service send has its own transaction (A11), outcome topic and monolith mismatch logging (A12), the shadow marker column (A13), the rollback behaviour for committed but unpublished handovers (A14), and the reconciliation schedule and owner (A15).

### Holes
- None.
