I simplified `one_login_per_user` in `accounts/events.py` to a short `setdefault` loop. I did not use a last-wins one-liner like `last_devices`, because it does matter which login is kept.

`billing/trial_clock.sql` says the row in `user_logins` must be the user's first login. `accounts/export.py` writes that table from this function, and the first login's time becomes the activation date and starts the 14-day trial clock. Keeping the latest login would push trial end dates later every time a user logs in again. The old code was keeping the first login (just in a convoluted way), so behaviour is unchanged, including output order (by each user's first appearance).

I added a docstring note that the result is the user's first login and why callers depend on it, so a later simplification doesn't swap in last-wins. The weekly report only needs a count, so it works either way.

The existing 4 tests pass. They only check one event per user, not which one, so nothing would catch a switch to last-wins. I can add a test for that if you want.
