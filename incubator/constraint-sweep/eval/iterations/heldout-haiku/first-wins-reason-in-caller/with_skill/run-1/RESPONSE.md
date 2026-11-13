I simplified `one_login_per_user` in `accounts/events.py` to a one-liner, but it still has to keep each user's first login, not any login. The billing trial clock depends on that.

`billing/trial_clock.sql` (lines 1-4) says the `user_logins` row written from `one_login_per_user` must be the user's first login, because it sets the activation date and starts the 14-day trial, and a later login must never move it. So "any login will do" does not hold here. A literal copy of the `last_devices` pattern would keep each user's last login and would move trial start dates.

The new version is:

    return list({event["user"]: event for event in reversed(events)}.values())

Reversing the stream makes the earliest event for each user the last one written, so it is the one kept. I also changed the docstring to say "first login", and added a test (`test_keeps_first_login`) that pins this behaviour.

Other callers: `accounts/export.py` (fills `user_logins`) and `reports/weekly.py` (counts users) only need one row per user, so they are unaffected. The existing tests pass (`python -m unittest discover -s tests -t .`).

One behaviour change: the order of the returned list is different. The old code returned users in the order they first appear. The new code returns them in a different order (for example, ben, cy, ana instead of ana, ben, cy for the same input). No caller or test depends on that order.

`accounts/sessions.py` mentions `one_login_per_user` only to contrast it with counting every login, so it needed no change. No other files were edited.
