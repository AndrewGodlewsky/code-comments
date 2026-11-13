I simplified `one_login_per_user` in `accounts/events.py` to a one-liner, but it still has to keep each user's first login, not any login. `billing/trial_clock.sql:2-4` says the `user_logins` row must be the user's FIRST login, because it sets the activation date and starts the 14-day trial clock, and a later login must never move it. `accounts/export.py` fills `user_logins` from this function, so a last-login one-liner like `last_devices` would have moved trial starts for every returning user.

The new body is `return list({event["user"]: event for event in reversed(events)}.values())`. Iterating in reverse makes the earliest event for each user the last write, so the first login wins.

Changes:
- `accounts/events.py`: the function is now the one-liner, and its docstring says it returns each user's first login event.
- `tests/test_events.py`: added `test_keeps_first_login_per_user`, which pins the first-login property. The existing tests did not check which login is kept.

Checks: `python -m unittest discover -s tests -t .` runs 5 tests and all pass.

One behaviour change: the result order. The old function returned users in order of their first login. The new one returns them in the reverse-iteration order of their last login. Nothing in the repo depends on that order: `export.py` inserts into a table keyed by `user`, `reports/weekly.py` takes `len`, and the test sorts. If order ever matters, the function needs a separate change.

Constraint sweep: searched the repo for `one_login_per_user`, `accounts.events` and `accounts/events`. Callers are `accounts/export.py`, `reports/weekly.py` and `tests/test_events.py`. The only live constraint is `billing/trial_clock.sql:2-4`, which the new code keeps. There are no stale constraints. `accounts/sessions.py:6` mentions the function only to contrast it with counting every login, and `reports/weekly.py:7` says any one event per user would do; neither needed a change.
