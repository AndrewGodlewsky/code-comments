I simplified `one_login_per_user` in `accounts/events.py` to a plain loop with `setdefault`. The function keeps each user's first login, not any login, so the one-liner style you suggested would not be right here. Tests pass (5 of 5).

Which login is kept matters. `billing/trial_clock.sql` says `user_logins` must hold each user's first login, because its date starts the 14-day trial and a later login must not move it. `accounts/export.py` fills that table from this function. The old code's reversed loop was doing exactly that: it kept the first login, although the name `latest_seen` suggested the opposite. The new docstring states the rule and the reason beside the code.

Changes:
- `accounts/events.py`: rewrote the function. Output and ordering are unchanged (each user's first login, ordered by first appearance). The old `kept not in ordered` check is gone.
- `accounts/events.py`: the docstring now says "first login" and gives the billing reason.
- `tests/test_events.py`: added `test_keeps_first_login_per_user`. The existing tests never checked which login was kept, so this guards the rule.

Left alone: `billing/trial_clock.sql` already states the rule. The comments in `reports/weekly.py` and `accounts/sessions.py` are still accurate.

Please confirm that the first login is the right one to keep for the trial clock. Your note said it did not matter, but the billing SQL says it does.
