I simplified `one_login_per_user` in `accounts/events.py`, but I did not make it a last_devices-style one-liner, because it does matter which login it keeps.

`billing/trial_clock.sql` says the `user_logins` row (written by `accounts/export.py` from this function) must be the user's FIRST login. That row is the activation date and starts the 14-day trial clock, and `billing/first_invoice.sql` bills off it. A last-wins one-liner like `last_devices` would let a later login push the trial end date out. The old code did keep the first login, but the reversed loop and `not in` scan hid that.

The new version is a short loop with `setdefault`. It keeps each user's first login, in order of first appearance, which is the same as before:

    first = {}
    for event in events:
        first.setdefault(event["user"], event)
    return list(first.values())

The docstring now states the first-login requirement and points at the SQL file. I added a test, `test_keeps_first_login`. The existing test only checked user names, so it would not have caught a switch to last-wins. All tests pass.

The other callers are unaffected. `reports/weekly.py` only counts users, so it is fine. A single dict comprehension can't keep the first login, because a dict comprehension keeps the last one.
