I simplified `one_login_per_user` in `accounts/events.py`. It is now a plain loop with `setdefault`, and it still keeps each user's first login, not an arbitrary one. I did not use a last-wins one-liner, because that would break billing.

What the grep found:

- `billing/trial_clock.sql` says the row in `user_logins` "must be the user's FIRST login". That row is the activation date and starts the 14-day trial clock, and a later login must never move it. `accounts/export.py` fills `user_logins` from `one_login_per_user`, so the first-login rule is a hard constraint.
- The current code already keeps the first login (its reversed loop ends with the earliest event per user). I checked this by running it before the change.
- The output order is by each user's first appearance in the stream. I kept that order.
- `accounts/devices.py` (`last_devices`) is a last-wins one-liner, but it is a different function and I left it alone. Copying its shape here, for example `{e["user"]: e for e in events}.values()`, would keep the latest login and move the trial clock.
- `reports/weekly.py` only uses the count, and `accounts/sessions.py` counts every login, so neither depends on which event is kept.

Changes:

- `accounts/events.py`: `one_login_per_user` now builds `first = {}`, calls `first.setdefault(event["user"], event)` for each event, and returns `list(first.values())`. The docstring says it keeps the first login and points to `billing/trial_clock.sql`.
- `tests/test_events.py`: added `test_keeps_each_users_first_login`. The existing tests did not check which login was kept.

Verification: `python -m unittest discover -s tests -t .` passes (5 tests). A before/after check on a sample stream gives the same output, `[('ana', 9, 'web'), ('ben', 10, 'ios')]`.

Not changed: `billing/trial_clock.sql`, `accounts/export.py` and `accounts/devices.py`. If you want the first-login rule enforced in code rather than only in the SQL comment, that would be a separate change.
