## Review of ms-02 (junior-v6, author sonnet, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Added a Terms block defining MailRelay, the broker (including who confirms to whom) and the flag, because Q1 and Q2 showed a newcomer cannot follow the ownership rules without them.
- Added a 'How it works today' paragraph and the types table (Q3, Q8).
- Message contract now says the service stores attempts and next_attempt_at and honours the wait, and that the monolith copies outcome and attempts to the row (Q4, Q5).
- Added the missing result_published column to the service table and described the result publisher and its republish loop in terms of it; removed the vague 'small service-side retry loop' wording (Q6).
- Broker-down handling in step 2 now says results wait in the table with result_published false.
- Reconciler now says what happens for in-progress rows, terminal rows and a down service, and that it repeats every 10 minutes (Q7).
- Added a labelled 'why first' note in step 4, a pointer from step 6 to the 60 s requirement, and an Open questions entry saying the brief gives no reason for the migration order (Q8).
- Step 2 state: added created_at and accepted_at columns to the service notifications table, because step 5 measures latency from them.
- Step 2 sender loop: stated the 1 s poll, one row per pass, immediate re-loop when a row was found, and that the consumer insert does not trigger it; accepted_at is set on success.
- Step 5 measurement: said the service computes latency from created_at and accepted_at and emits it as a metric, not through the result message.
- Message contract: noted that the accept time is not in notifications.result.
- Reordered into the required layout: summary (including how today's system works), terms, a 'How the system runs' section, then a separate 'Rollout steps' section, residual risks and open questions.
- Moved the service and monolith component descriptions (consumer, sender loop, result publisher, pager, forwarder, result consumer, reconciler) out of steps 2 and 3 into one runtime section; steps 2 and 3 now only say what to build, deploy and check.
- Merged the scattered failure bullets of steps 2 and 3 into one failure table for the running system.
- Merged the 'Why first' reasoning and the open question; kept both because the inference is flagged as not from the brief.
- Added terms for MailRelay duplicate behaviour, broker confirmation, flag, old worker and forwarder, and folded the types table into the terms (from questions about what these are).
- Added a short account of today's worker and the 30 duplicates a week to the summary.
- Kept result_published, accepted_at and the next_attempt_at handoff where they apply; removed the 'see step 5' pointer for the accept time.
- Shortened steps 5 and 6 by pointing to step 4 for shared data, state, failures and rollback, but kept the p99 breakdown, first-attempt failure note and the 45 s and 30 s alerts.
- Merged the repeated 'same key collapses duplicates' explanations into one place; removed the duplicate rollback explanations.
- Checked the first version line by line: retained the 30 day retention, 15 minute retry window, version gate, template freeze, soak lengths, 7 day decommission, 12 h runbook rule and all alerts. Left out only exact column naming beyond what the service needs.

### Holes
- None.
