## Review of ms-02 (junior-v7, author sonnet, seeded-implicit)

Rounds: 2. Ended: teachback-correct.

### What changed
- Rewrote the plan in the skill's order: summary with how today's system works, terms, fixed rules, numbered steps, rollback, failures, open questions.
- Defined MailRelay, broker, flag, route, outbox relay and deliveries in a terms list (Q2-Q5).
- Specified that route is stamped at insert from the type's flag and fixed per row, and that the old worker filters on route='monolith' (Q3, Q4, Q9).
- Specified the outbox relay: poll every second, publish full content, wait for confirmation, mark handed_off; broker-down handling (Q5).
- Specified message contents (Q6) and consumer dedupe by id with insert-then-acknowledge (Q7).
- Specified service retry state in deliveries and the 5 attempts / 1-2-4-8 minute policy, failed plus page on-call (Q8).
- Added a Rollback section: in-flight rows finish on their original path, service must stay running (Q9).
- Restored brief facts the first version dropped: 3-day soak per type, p99 under 60 s gate for password_reset, 7-day wait before removing the old worker, ordering of types.
- Added a failure table and one open question about final status visibility in the monolith.
- Step 4: relay runs on every instance, claims rows with SKIP LOCKED, and uses pending/handed_off status so unpublished rows are identifiable.
- Step 3 consumer: if the deliveries insert fails, do not acknowledge so the broker redelivers.
- Step 3 sender: poll every second, other instances skip locked rows, and the MailRelay call has a client timeout.
- Terms and steps 3 and 6: added created_at and sent_at to deliveries and defined latency as sent_at minus created_at.
- Step 3: the service has its own template copy, and template changes are made in both places until step 8.
- Failures table: added service database down and failed-row rows, and widened the MailRelay row to cover a hang.
- Open questions: added the on-call handling of failed rows, the timeout value, and clock skew.
- Merged the Route/Flag details: flag is read at insert, who reads route (old worker vs relay) now stated once in Terms.
- Added a Message term (full content, so no lookup) and moved the reason for the outbox relay (broker cannot join the DB transaction) into its definition.
- Added today's mail-flow description (5 s poll, batch of 50, per-batch commit) to the summary, and noted MailRelay has no key today.
- Restated brief facts previously dropped or thin: table is first record, rendering moves to service, rollback within a minute with nothing lost or re-sent, nothing-lost/nothing-duplicated rule.
- Shortened step 4 and step 3 wording; removed the repeated 'Starts:' labels in favor of inline starts; cut the repeated note about rollback paths across steps.
- No open questions removed; all four kept.

### Holes
- Q16: After a row is marked failed (on either side), does anything resend it or does a person act on it? What does on-call do with the page? (author: Nothing resends a failed row automatically, on either side, which matches today's code. Today's code only pages on-call. I do not know what the on-call runbook tells a person to do with the page, or whether a manual resend after 24 hours needs a new key. Added to the Failures table and the open questions without inventing a procedure.)
