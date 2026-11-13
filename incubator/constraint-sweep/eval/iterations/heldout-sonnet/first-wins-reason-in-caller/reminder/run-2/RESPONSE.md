I simplified `one_login_per_user` in `accounts/events.py`, but it still keeps each user's FIRST login. I did not make it a `last_devices`-style one-liner, because which login it keeps does matter.

`billing/trial_clock.sql` says the `user_logins` row written by `accounts/export.py` from this function "must be the user's FIRST login". That row is the activation date and starts the 14-day trial clock. Keeping the last login would push trial end dates later and delay first invoices. The old code was first-wins too, just indirectly (a reversed loop plus a dedupe pass). `last_devices` is last-wins, so copying it would have broken billing.

The new version is a short loop with `dict.setdefault`. It returns the same output as before: first event per user, in order of first appearance.

- **Comment:** I added a note to the docstring saying callers rely on first-wins, with the reason.
- **Test:** I added `test_keeps_first_login`, since nothing tested which login is kept before. The existing tests passed and the new one passes.
- **Other callers:** `reports/weekly.py` only counts users, so it doesn't care. The comment in `accounts/sessions.py` is unaffected.
