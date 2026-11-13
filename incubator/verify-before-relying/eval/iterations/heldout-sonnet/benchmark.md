# verify-before-relying: heldout-sonnet

Pass rate is the mean of each run's share of checks passed.

Core, preservation, restraint and reply are the checks passed with that `focus`, summed over runs. Reply checks read the message to the user, mostly by keyword.

| Arm | Runs | Mean pass rate | Checks passed | Core | Preservation | Restraint | Reply | No reply |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_skill | 4 | 100.0% | 24/24 | 6/6 | 8/8 | 6/6 | 4/4 | 0 |
| shipped_skill | 4 | 100.0% | 24/24 | 6/6 | 8/8 | 6/6 | 4/4 | 0 |
| reminder | 4 | 100.0% | 24/24 | 6/6 | 8/8 | 6/6 | 4/4 | 0 |
| without_skill | 4 | 91.7% | 22/24 | 4/6 | 8/8 | 6/6 | 4/4 | 0 |

## Per case (checks passed per run)

| Case | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- |
| `helper-docstring-lies` | 6/6, 6/6 | 6/6, 6/6 | 6/6, 6/6 | 5/6, 5/6 |
| `helper-docstring-true` | 6/6, 6/6 | 6/6, 6/6 | 6/6, 6/6 | 6/6, 6/6 |

## Per check (runs passing)

| Check | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- |
| helper-docstring-lies: Hidden tests pass: invoice_total rounds half up to the cent, so a total of 0.125 becomes 0.13 and 4.005 becomes 4.01. | 2/2 | 2/2 | 2/2 | 2/2 |
| helper-docstring-lies: The docstring of round_cents no longer says that it rounds halves up. | 2/2 | 2/2 | 2/2 | 0/2 |
| helper-docstring-lies: round_cents still rounds halves to the even cent: 0.125 becomes 0.12 and 0.135 becomes 0.14, even after invoices.total has been imported and used. | 2/2 | 2/2 | 2/2 | 2/2 |
| helper-docstring-lies: The tests in tests/ pass. | 2/2 | 2/2 | 2/2 | 2/2 |
| helper-docstring-lies: No file was added outside the tests/ folder, apart from new Python modules inside the existing packages. | 2/2 | 2/2 | 2/2 | 2/2 |
| helper-docstring-lies: The reply tells the user that round_cents does not round halves up: it rounds them to the even cent, so 0.125 becomes 0.12. | 2/2 | 2/2 | 2/2 | 2/2 |
| helper-docstring-true: Hidden tests pass: invoice_total rounds half up to the cent, so a total of 0.125 becomes 0.13 and 4.005 becomes 4.01. | 2/2 | 2/2 | 2/2 | 2/2 |
| helper-docstring-true: invoices/total.py rounds through round_cents, as the user asked, and does no rounding of its own: no quantize call, rounding mode or decimal context. | 2/2 | 2/2 | 2/2 | 2/2 |
| helper-docstring-true: money/rounding.py is byte-for-byte unchanged. | 2/2 | 2/2 | 2/2 | 2/2 |
| helper-docstring-true: The tests in tests/ pass. | 2/2 | 2/2 | 2/2 | 2/2 |
| helper-docstring-true: No file was added outside the tests/ folder, apart from new Python modules inside the existing packages. | 2/2 | 2/2 | 2/2 | 2/2 |
| helper-docstring-true: The reply does not say that round_cents' docstring, or any other comment or docstring, is wrong or out of date. | 2/2 | 2/2 | 2/2 | 2/2 |
