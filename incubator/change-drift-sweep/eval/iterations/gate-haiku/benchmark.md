# change-drift-sweep: gate-haiku

Pass rate is the mean of each run's share of checks passed.

Core, preservation, restraint and reply are the checks passed with that `focus`, summed over runs. Reply checks read the message to the user, mostly by keyword.

| Arm | Runs | Mean pass rate | Checks passed | Core | Preservation | Restraint | Reply | No reply |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| without_skill | 14 | 99.0% | 87/88 | 51/52 | 26/26 | 8/8 | 2/2 | 0 |

## Per case (checks passed per run)

| Case | without_skill |
| --- | --- |
| `default-value-drift` | 6/7, 7/7 |
| `derived-backoff-total` | 6/6, 6/6 |
| `flag-rename-records-stay` | 7/7, 7/7 |
| `pointer-comment-needs-nothing` | 6/6, 6/6 |
| `poll-interval-average-wait` | 6/6, 6/6 |
| `pre-existing-drift-reported` | 6/6, 6/6 |
| `unit-spelled-ttl` | 6/6, 6/6 |

## Per check (runs passing)

| Check | without_skill |
| --- | --- |
| default-value-drift: PAGE_SIZE is 200 and fetch_changed asks the ledger API for 200 rows a request; the request timeout is unchanged (hidden tests). | 2/2 |
| default-value-drift: Every living description of the page size gives the new one: no comment, docstring, README or docs sentence outside the records mentions pages, rows or requests together with 50 or fifty, and every changed or added sentence that gives a page size gives 200. | 1/2 |
| default-value-drift: docs/api.md still says how many rows a page holds, and says 200 (or names PAGE_SIZE). | 2/2 |
| default-value-drift: The dated load-test report is byte-identical and every released CHANGELOG.md section is unchanged, because both are true about their dates. | 2/2 |
| default-value-drift: docs/limits.md, the ledger team's 500-row limit, is byte-identical. | 2/2 |
| default-value-drift: Every other comment, docstring and doc line that was accurate, such as "Pages are numbered from 1" and the transaction sentence in exporter/sync.py, is kept word for word. | 2/2 |
| default-value-drift: The repository's tests pass. | 2/2 |
| derived-backoff-total: send_alert makes six attempts with waits of 1, 2, 4, 8 and 16 seconds, and the other delivery settings are unchanged (hidden tests). | 2/2 |
| derived-backoff-total: No comment, docstring or doc still states a figure derived from four attempts ("four attempts", the waits "1, 2 and 4", a total of 7 s or seven seconds, or 200 POSTs) or narrates one as history (previously 7, was four, from 200). | 2/2 |
| derived-backoff-total: Every figure in a changed or added prose line agrees with six attempts: waits and totals in seconds are among 1, 2, 4, 8, 16 and 31 (about 30 accepted), attempts are 6, retries are 5 and the storm sends 300 POSTs. | 2/2 |
| derived-backoff-total: docs/oncall.md still tells on-call when an alert is dropped and how many POSTs the 50-alert storm sends, with the new figures: about 31 seconds (or half a minute) and 300. | 2/2 |
| derived-backoff-total: Prose that was still true is kept word for word, including the BASE_DELAY_S comment, the 503 draining note, the 7-day outbox retention in code and docs, and the log advice in docs/oncall.md. | 2/2 |
| derived-backoff-total: The repository's tests pass. | 2/2 |
| flag-rename-records-stay: reportctl export filters rows with --after, rejects --since, and backfill still writes the right files (hidden tests). | 2/2 |
| flag-rename-records-stay: No living description names --since: the README, docs/cli.md, the backfill runbook and every comment and docstring are free of it (CHANGELOG.md and docs/adr/ are records and are not checked here). | 2/2 |
| flag-rename-records-stay: The README usage example and the docs/cli.md options table show --after. | 2/2 |
| flag-rename-records-stay: Every released CHANGELOG.md section is unchanged and the original [Unreleased] lines are kept; any new line sits in the [Unreleased] section. | 2/2 |
| flag-rename-records-stay: docs/adr/0002-incremental-export.md is byte-identical. | 2/2 |
| flag-rename-records-stay: Every other comment, docstring and doc line that was accurate is kept word for word once --since reads --after, including the policy line in docs/adr/README.md (the released CHANGELOG sections and ADR 0002 are checked by 04 and 05). | 2/2 |
| flag-rename-records-stay: The repository's tests pass. | 2/2 |
| pointer-comment-needs-nothing: MAX_PARALLEL is 8: eight jobs run at once and never more, and MAX_TRIES is still 4 (hidden tests). | 2/2 |
| pointer-comment-needs-nothing: Every existing comment and docstring in jobs/ is kept word for word, and no line added there copies the new value or notes the old one. | 2/2 |
| pointer-comment-needs-nothing: docs/operations.md and README.md are byte-identical: the pointer to MAX_PARALLEL, the four tries and the four-second dashboard refresh were all still true, and the README states no value. | 2/2 |
| pointer-comment-needs-nothing: The dated capacity report is byte-identical and every released CHANGELOG.md section is unchanged. | 2/2 |
| pointer-comment-needs-nothing: No comment, docstring or doc line added anywhere else (outside jobs/, docs/operations.md, README.md and CHANGELOG.md) states the new value (8 or eight) or narrates the change (was 4, from 4, raised, increased, previously). | 2/2 |
| pointer-comment-needs-nothing: The repository's tests pass. | 2/2 |
| poll-interval-average-wait: POLL_INTERVAL_S is 600, so the next poll is due 600 seconds after the last and run() waits 600 seconds between polls; PAGE_LIMIT is unchanged (hidden tests). | 2/2 |
| poll-interval-average-wait: No living comment, docstring or doc sentence about polling or order delay still gives the old interval or a figure derived from it (every five minutes, every 5 min, five minutes after, an average of two and a half minutes), and every changed or added one gives figures that fit ten-minute polls: ten minutes for the interval and the longest delay, five minutes for the average wait (the cache sentence and the dated incident entry are not checked here). | 2/2 |
| poll-interval-average-wait: README.md still says how long a new order waits on average, as five minutes (5 min, 300 seconds) or as half the time between polls with no stale figure, and docs/operations.md gives the new interval (10 min, ten minutes, 600 seconds or POLL_INTERVAL_S). | 2/2 |
| poll-interval-average-wait: The storefront's 5-minute cache sentence and its 10,000-calls-a-day quota are unchanged word for word, and so is every line of the dated 2 October 2026 entry under "Past incidents" in docs/operations.md. | 2/2 |
| poll-interval-average-wait: Every other comment, docstring and doc line that was accurate is kept word for word. | 2/2 |
| poll-interval-average-wait: The repository's tests pass. | 2/2 |
| pre-existing-drift-reported: BATCH_SIZE is 250, so the 250th notification sends a batch and the 249th does not, while the flush interval is still 30 seconds (hidden tests). | 2/2 |
| pre-existing-drift-reported: No comment, docstring or doc sentence about batches or provider calls still gives the old size as 100, a hundred or one hundred, and every changed or added one that gives a batch size gives 250. | 2/2 |
| pre-existing-drift-reported: The sentence "A partial batch is flushed after 60 seconds, so a notification is never held longer than a minute." in docs/notifications.md is either unchanged or corrected toward the code (30 seconds, or naming FLUSH_INTERVAL_S) with every other word kept. The change did not cause that mismatch, so the sentence is neither rewritten nor removed. | 2/2 |
| pre-existing-drift-reported: Every other comment, docstring and doc line that was accurate, including the provider's 500-per-call limit, is kept word for word. | 2/2 |
| pre-existing-drift-reported: The reply tells the user, in one paragraph, that docs/notifications.md gave a 60-second (one-minute) flush while FLUSH_INTERVAL_S is 30, whether or not the run corrected the doc. | 2/2 |
| pre-existing-drift-reported: The repository's tests pass. | 2/2 |
| unit-spelled-ttl: SESSION_TTL_S is 1800: a session idle for 20 minutes survives and one idle for 31 minutes ends, while reset links and lockout keep their limits (hidden tests). | 2/2 |
| unit-spelled-ttl: No comment, docstring or doc sentence about sessions or idle time still gives the old timeout as fifteen minutes, 15 min or 900 seconds, and every changed or added one that gives a length of time gives 30 minutes (thirty minutes, half an hour or 1800 seconds). | 2/2 |
| unit-spelled-ttl: docs/security.md still states the idle-session timeout, as 30 minutes (thirty minutes, half an hour, 1800 seconds, or by naming SESSION_TTL_S). | 2/2 |
| unit-spelled-ttl: The statements that share the figure but describe something else stay word for word: the identity provider's 15-minute tokens, the 15-minute reset links in docs/security.md and auth/reset.py, and the 15 failed sign-ins in docs/security.md and auth/lockout.py. | 2/2 |
| unit-spelled-ttl: Every other comment, docstring and doc line that was accurate is kept word for word. | 2/2 |
| unit-spelled-ttl: The repository's tests pass. | 2/2 |
