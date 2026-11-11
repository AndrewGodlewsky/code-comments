I simplified `one_login_per_user` in `accounts/events.py`, but it still keeps each user's first login, not any login. I did not switch to last-login the way `last_devices` works.

Reason: `billing/trial_clock.sql` (lines 2-5) says the row written from `one_login_per_user` must be the user's first login, because it sets the activation date and starts the 14-day trial clock, and a later login must never move it. A last-login rule would shift trial end dates for every user who logged in again. That is a live constraint, so I kept first-wins.

The new version is a single pass that keeps the first event seen for each user, in order of each user's first login:

    first = {}
    for event in events:
        first.setdefault(event["user"], event)
    return list(first.values())

Output matches the old function for every input I checked by reasoning, including ordering.

Other changes:
- Docstring now says "first login" and points to `billing/trial_clock.sql`.
- Added `test_keeps_first_login_per_user` to `tests/test_events.py`. The existing tests did not pin which login is kept.

Checked the other callers: `reports/weekly.py` (counts users) and `accounts/export.py` (fills `user_logins`) are unaffected. `accounts/sessions.py` mentions `one_login_per_user` only to say it counts differently; no change needed there.

Tests: all 5 pass (`python -m unittest discover -s tests -t .`).

If you do want last-login, the trial clock has to change first, and that is a billing decision.
