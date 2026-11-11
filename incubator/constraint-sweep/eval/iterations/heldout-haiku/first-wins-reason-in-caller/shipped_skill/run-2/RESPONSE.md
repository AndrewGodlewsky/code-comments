I simplified `one_login_per_user` in `accounts/events.py`, but it still keeps each user's first login, not any login. The one-liner pattern from `last_devices` would have changed behaviour.

The rule matters because `billing/trial_clock.sql` builds a view over `user_logins`, whose rows come from `one_login_per_user` via `accounts/export.py`. That SQL comment says the row must be the user's first login, since it is the activation date that starts the 14-day trial clock. Keeping the latest login would move the trial start forward on every login.

The new version is a single `setdefault` loop over the events, returning the first event per user in the order those first logins appear. Output is identical to the old code: on a sample stream it returns the same first-login events in the same order.

Changes:
- `accounts/events.py`: rewritten. The docstring now states the first-login contract, and a short comment records the reason and points to `billing/trial_clock.sql`.
- `tests/test_events.py`: added `test_keeps_first_login_per_user`. The old tests did not check which login was kept, and the old code's reversed loop was the only sign of that rule.

Tests: all 5 pass (`python -m unittest discover -s tests -t .`).

Not changed: `accounts/sessions.py`, `reports/weekly.py`, `accounts/export.py` and `billing/trial_clock.sql` still read correctly against the new code.

If you actually want the latest login per user, that is a behaviour change, and `billing/trial_clock.sql` would need its trial-clock logic and comment reworked too. I did not make that change.
