I simplified `one_login_per_user` in `accounts/events.py` to a single loop using `setdefault`. It now keeps each user's first login, in the order users first appear, which is exactly what the old code did.

I did not use the one-liner pattern from `last_devices`. That pattern (`{event["user"]: event for event in events}`) keeps the last event per user, and this function's output is not safe to change that way. `billing/trial_clock.sql` starts the 14-day trial from the row that `export_user_logins` writes using this function, and its comment says that row must be the user's first login so a later login never moves the trial start. A last-login version would silently move activation dates for every user with more than one login.

The old code's variable name `latest_seen` was misleading: its reversed loop ends up keeping the earliest event. I added a docstring note that the first login is intentional and points at the SQL view, so this does not get "fixed" later.

I also added a test, `test_keeps_first_login_per_user`, that pins the first-login behavior. All four tests in `tests/test_events.py` pass, and a manual check on a three-event stream gives the same output as before.

Callers (`reports/weekly.py` counts users, `accounts/export.py` writes the table) are unaffected.
