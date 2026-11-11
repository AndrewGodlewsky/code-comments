# change-drift-sweep: heldout-haiku

Pass rate is the mean of each run's share of checks passed.

Core, preservation, restraint and reply are the checks passed with that `focus`, summed over runs. Reply checks read the message to the user, mostly by keyword.

| Arm | Runs | Mean pass rate | Checks passed | Core | Preservation | Restraint | Reply | No reply |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_skill | 6 | 100.0% | 36/36 | 18/18 | 9/9 | 9/9 | - | 0 |
| shipped_skill | 6 | 97.2% | 35/36 | 17/18 | 9/9 | 9/9 | - | 0 |
| reminder | 6 | 100.0% | 36/36 | 18/18 | 9/9 | 9/9 | - | 0 |
| without_skill | 6 | 94.4% | 34/36 | 16/18 | 9/9 | 9/9 | - | 0 |

## Per case (checks passed per run)

| Case | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- |
| `pointer-comment-needs-nothing` | 6/6, 6/6, 6/6 | 6/6, 6/6, 6/6 | 6/6, 6/6, 6/6 | 6/6, 6/6, 6/6 |
| `poll-interval-average-wait` | 6/6, 6/6, 6/6 | 6/6, 6/6, 5/6 | 6/6, 6/6, 6/6 | 5/6, 5/6, 6/6 |

## Per check (runs passing)

| Check | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- |
| pointer-comment-needs-nothing: MAX_PARALLEL is 8: eight jobs run at once and never more, and MAX_TRIES is still 4 (hidden tests). | 3/3 | 3/3 | 3/3 | 3/3 |
| pointer-comment-needs-nothing: Every existing comment and docstring in jobs/ is kept word for word, and no line added there copies the new value or notes the old one. | 3/3 | 3/3 | 3/3 | 3/3 |
| pointer-comment-needs-nothing: docs/operations.md and README.md are byte-identical: the pointer to MAX_PARALLEL, the four tries and the four-second dashboard refresh were all still true, and the README states no value. | 3/3 | 3/3 | 3/3 | 3/3 |
| pointer-comment-needs-nothing: The dated capacity report is byte-identical and every released CHANGELOG.md section is unchanged. | 3/3 | 3/3 | 3/3 | 3/3 |
| pointer-comment-needs-nothing: No comment, docstring or doc line added anywhere else (outside jobs/, docs/operations.md, README.md and CHANGELOG.md) states the new value (8 or eight) or narrates the change (was 4, from 4, raised, increased, previously). | 3/3 | 3/3 | 3/3 | 3/3 |
| pointer-comment-needs-nothing: The repository's tests pass. | 3/3 | 3/3 | 3/3 | 3/3 |
| poll-interval-average-wait: POLL_INTERVAL_S is 600, so the next poll is due 600 seconds after the last and run() waits 600 seconds between polls; PAGE_LIMIT is unchanged (hidden tests). | 3/3 | 3/3 | 3/3 | 3/3 |
| poll-interval-average-wait: No living comment, docstring or doc sentence about polling or order delay still gives the old interval or a figure derived from it (every five minutes, every 5 min, five minutes after, an average of two and a half minutes or about 150 s), and every changed or added one gives figures that fit ten-minute polls: ten minutes for the interval and the longest delay, five minutes (300 s) for the average wait (the cache sentence, the packers' five minutes and the dated incident entry are not checked here). | 3/3 | 2/3 | 3/3 | 1/3 |
| poll-interval-average-wait: docs/fulfilment.md still says how long a new order waits on average, as five minutes (5 min, 300 seconds) or as half the time between polls with no stale figure, and docs/operations.md gives the new interval (10 min, ten minutes, 600 seconds or POLL_INTERVAL_S). | 3/3 | 3/3 | 3/3 | 3/3 |
| poll-interval-average-wait: The storefront's 5-minute cache sentence and its 10,000-calls-a-day quota are unchanged word for word, and so are the packers' five minutes to confirm a picked order in docs/fulfilment.md and every line of the dated 2 October 2026 entry under "Past incidents" in docs/operations.md. | 3/3 | 3/3 | 3/3 | 3/3 |
| poll-interval-average-wait: Every other comment, docstring and doc line that was accurate is kept word for word. | 3/3 | 3/3 | 3/3 | 3/3 |
| poll-interval-average-wait: The repository's tests pass. | 3/3 | 3/3 | 3/3 | 3/3 |
