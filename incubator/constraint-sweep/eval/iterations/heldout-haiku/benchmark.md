# constraint-sweep: heldout-haiku

Pass rate is the mean of each run's share of checks passed.

Core, preservation, restraint and reply are the checks passed with that `focus`, summed over runs. Reply checks read the message to the user, mostly by keyword.

| Arm | Runs | Mean pass rate | Checks passed | Core | Preservation | Restraint | Reply | No reply |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_skill | 6 | 100.0% | 33/33 | 6/6 | 9/9 | 15/15 | 3/3 | 0 |
| shipped_skill | 6 | 100.0% | 33/33 | 6/6 | 9/9 | 15/15 | 3/3 | 0 |
| reminder | 6 | 96.7% | 32/33 | 6/6 | 9/9 | 14/15 | 3/3 | 0 |
| without_skill | 6 | 100.0% | 33/33 | 6/6 | 9/9 | 15/15 | 3/3 | 0 |

## Per case (checks passed per run)

| Case | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- |
| `first-wins-reason-in-caller` | 6/6, 6/6, 6/6 | 6/6, 6/6, 6/6 | 6/6, 6/6, 6/6 | 6/6, 6/6, 6/6 |
| `mention-without-constraint` | 5/5, 5/5, 5/5 | 5/5, 5/5, 5/5 | 4/5, 5/5, 5/5 | 5/5, 5/5, 5/5 |

## Per check (runs passing)

| Check | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- |
| first-wins-reason-in-caller: Hidden tests: with repeated users, one_login_per_user keeps exactly one event per user, and it is that user's first event, so the trial clock in billing/trial_clock.sql starts at each user's first login. | 3/3 | 3/3 | 3/3 | 3/3 |
| first-wins-reason-in-caller: one_login_per_user was rewritten: its code differs from the original. | 3/3 | 3/3 | 3/3 | 3/3 |
| first-wins-reason-in-caller: The repository's own tests pass. | 3/3 | 3/3 | 3/3 | 3/3 |
| first-wins-reason-in-caller: billing/trial_clock.sql keeps its SQL, and every one of its comment lines is kept. | 3/3 | 3/3 | 3/3 | 3/3 |
| first-wins-reason-in-caller: At most three comment or docstring lines are added to source files outside tests/, counted net: a reworded or re-wrapped line is not an added line. | 3/3 | 3/3 | 3/3 | 3/3 |
| first-wins-reason-in-caller: Every file other than accounts/events.py, billing/trial_clock.sql and tests/ is byte-for-byte unchanged: files that were only read were not edited. | 3/3 | 3/3 | 3/3 | 3/3 |
| mention-without-constraint: Hidden tests: with "CHF", round_price rounds to the nearest 0.05; with no currency it rounds exactly as before, and every caller's result is unchanged. | 3/3 | 3/3 | 3/3 | 3/3 |
| mention-without-constraint: Every file outside pricing/rounding.py and tests/ is unchanged: nothing that only mentions round_price was edited. | 3/3 | 3/3 | 2/3 | 3/3 |
| mention-without-constraint: At most three comment or docstring lines are added to source files outside tests/, counted net: a reworded or re-wrapped line is not an added line. | 3/3 | 3/3 | 3/3 | 3/3 |
| mention-without-constraint: The repository's own tests pass. | 3/3 | 3/3 | 3/3 | 3/3 |
| mention-without-constraint: The reply asks the user no question about round_price's callers or the files that mention it. | 3/3 | 3/3 | 3/3 | 3/3 |
