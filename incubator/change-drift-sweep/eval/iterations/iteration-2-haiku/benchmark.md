# change-drift-sweep: iteration-2-haiku

Pass rate is the mean of each run's share of checks passed.

Core, preservation, restraint and reply are the checks passed with that `focus`, summed over runs. Reply checks read the message to the user, mostly by keyword.

| Arm | Runs | Mean pass rate | Checks passed | Core | Preservation | Restraint | Reply | No reply |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_skill | 15 | 100.0% | 96/96 | 60/60 | 30/30 | 3/3 | 3/3 | 0 |

## Per case (checks passed per run)

| Case | with_skill |
| --- | --- |
| `default-value-drift` | 7/7, 7/7, 7/7 |
| `derived-backoff-total` | 6/6, 6/6, 6/6 |
| `flag-rename-records-stay` | 7/7, 7/7, 7/7 |
| `pre-existing-drift-reported` | 6/6, 6/6, 6/6 |
| `unit-spelled-ttl` | 6/6, 6/6, 6/6 |

## Per check (runs passing)

| Check | with_skill |
| --- | --- |
| default-value-drift: PAGE_SIZE is 200 and fetch_changed asks the ledger API for 200 rows a request; the request timeout is unchanged (hidden tests). | 3/3 |
| default-value-drift: Every living description of the page size gives the new one: no comment, docstring, README or docs sentence outside the records mentions pages, rows or requests together with 50 or fifty, and every changed or added sentence that gives a page size gives 200. | 3/3 |
| default-value-drift: docs/api.md still says how many rows a page holds, and says 200 (or names PAGE_SIZE). | 3/3 |
| default-value-drift: The dated load-test report is byte-identical and every released CHANGELOG.md section is unchanged, because both are true about their dates. | 3/3 |
| default-value-drift: docs/limits.md, the ledger team's 500-row limit, is byte-identical. | 3/3 |
| default-value-drift: Every other comment, docstring and doc line that was accurate, such as "Pages are numbered from 1" and the transaction sentence in exporter/sync.py, is kept word for word. | 3/3 |
| default-value-drift: The repository's tests pass. | 3/3 |
| derived-backoff-total: send_alert makes six attempts with waits of 1, 2, 4, 8 and 16 seconds, and the other delivery settings are unchanged (hidden tests). | 3/3 |
| derived-backoff-total: No comment, docstring or doc still states a figure derived from four attempts ("four attempts", the waits "1, 2 and 4", a total of 7 s or seven seconds, 200 POSTs, an alert retried three times, or a 40-alert backlog cleared in under five minutes) or narrates one as history (previously 7, was four, from 200). | 3/3 |
| derived-backoff-total: Every figure in a changed or added prose line agrees with six attempts: waits and totals in seconds are among 1, 2, 4, 8, 16 and 31 (about 30 accepted), the 40-alert backlog takes about 21 minutes (1240 s, or an upper bound up to half an hour), attempts are 6, retries are 5 and the storm sends 300 POSTs. | 3/3 |
| derived-backoff-total: docs/oncall.md still tells on-call when an alert is dropped and how many POSTs the 50-alert storm sends, with the new figures: about 31 seconds (or half a minute) and 300; and the gateway-maintenance runbook still says how often an alert is retried, as five times (or six attempts, or by naming MAX_ATTEMPTS). | 3/3 |
| derived-backoff-total: Prose that was still true is kept word for word, including the BASE_DELAY_S comment, the 503 draining note, the 7-day outbox retention in code and docs, and the log advice in docs/oncall.md. | 3/3 |
| derived-backoff-total: The repository's tests pass. | 3/3 |
| flag-rename-records-stay: reportctl export filters rows with --after, rejects --since, and backfill still writes the right files (hidden tests). | 3/3 |
| flag-rename-records-stay: No living description names --since, or still says the option shares its name with the orders API's filter, which is still called `since`: the README, docs/cli.md, the backfill runbook and every comment and docstring are free of both (CHANGELOG.md, docs/adr/ and docs/incidents/ are records and are not checked here). | 3/3 |
| flag-rename-records-stay: The README usage example and the docs/cli.md options table show --after. | 3/3 |
| flag-rename-records-stay: Every released CHANGELOG.md section is unchanged and the original [Unreleased] lines are kept; any new line sits in the [Unreleased] section. | 3/3 |
| flag-rename-records-stay: The records are byte-identical: docs/adr/0002-incremental-export.md, and the dated incident report docs/incidents/2026-07-14-missed-night.md, whose command is the one that was run that day. | 3/3 |
| flag-rename-records-stay: Every other comment, docstring and doc line that was accurate is kept word for word once --since reads --after, including the policy line in docs/adr/README.md and the orders API's own `since=` query in docs/cli.md (the released CHANGELOG sections, ADR 0002 and the incident report are checked by 04 and 05). | 3/3 |
| flag-rename-records-stay: The repository's tests pass. | 3/3 |
| pre-existing-drift-reported: BATCH_SIZE is 250, so the 250th notification sends a batch and the 249th does not, while the flush interval is still 30 seconds (hidden tests). | 3/3 |
| pre-existing-drift-reported: No comment, docstring or doc sentence about batches or provider calls still gives the old size as 100, a hundred or one hundred, or a figure worked out from it (10 calls for a burst of 1,000 notifications, 2,000 notifications a second at 20 calls a second), and every changed or added one gives figures that fit 250: batches of 250, 4 calls for the burst and 5,000 notifications a second. | 3/3 |
| pre-existing-drift-reported: The sentence "A partial batch is flushed after 60 seconds, so a notification is never held longer than a minute." in docs/notifications.md is either unchanged or corrected toward the code (30 seconds, or naming FLUSH_INTERVAL_S) with every other word kept. The change did not cause that mismatch, so the sentence is neither rewritten nor removed. | 3/3 |
| pre-existing-drift-reported: Every other comment, docstring and doc line that was accurate, including the provider's 500-per-call limit, is kept word for word. | 3/3 |
| pre-existing-drift-reported: The reply tells the user, in one paragraph, that docs/notifications.md gave a 60-second (one-minute) flush while FLUSH_INTERVAL_S is 30, whether or not the run corrected the doc. | 3/3 |
| pre-existing-drift-reported: The repository's tests pass. | 3/3 |
| unit-spelled-ttl: SESSION_TTL_S is 1800: a session idle for 20 minutes survives and one idle for 31 minutes ends, while reset links and lockout keep their limits (hidden tests). | 3/3 |
| unit-spelled-ttl: No comment, docstring or doc sentence about sessions, idle time or the "Still there?" banner still gives the old timeout in any form (fifteen minutes, 15 min, 900 seconds, a quarter of an hour) or the banner time it set (14 minutes), and every changed or added one gives 30 minutes for the timeout (thirty minutes, half an hour or 1800 seconds) and 29 minutes for the banner. | 3/3 |
| unit-spelled-ttl: docs/security.md still states the idle-session timeout, as 30 minutes (thirty minutes, half an hour, 1800 seconds, or by naming SESSION_TTL_S), and docs/console.md still says when the "Still there?" banner appears, as 29 minutes (or a minute before the session ends, or by naming IDLE_WARNING_S). | 3/3 |
| unit-spelled-ttl: The statements that share the figure but describe something else stay word for word: the identity provider's 15-minute tokens, the 15-minute reset links in docs/security.md and auth/reset.py, and the 15 failed sign-ins in docs/security.md and auth/lockout.py. | 3/3 |
| unit-spelled-ttl: Every other comment, docstring and doc line that was accurate is kept word for word. | 3/3 |
| unit-spelled-ttl: The repository's tests pass. | 3/3 |
