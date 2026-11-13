I simplified `one_login_per_user` in `accounts/events.py` to a plain first-wins loop. It still keeps each user's first login, which matters here, so I did not switch to the `last_devices` pattern.

The function now reads:

```python
def one_login_per_user(events):
    """Return each user's first login event, in order of each user's first login."""
    first_logins = {}
    for event in events:
        first_logins.setdefault(event["user"], event)
    return list(first_logins.values())
```

Why it can't keep the latest login, as the `last_devices` pattern would:

- `billing/trial_clock.sql` says the row written to `user_logins` must be the user's first login. That row sets the activation date and starts the 14-day trial clock, and a later login must never move it.
- `accounts/export.py` writes `user_logins` from `one_login_per_user`, so changing which login is kept would move trial end dates.
- `reports/weekly.py` only counts users, so it doesn't care which login is kept.

The old code also kept the first login. Its reversed loop let the earliest event overwrite the others. The new version gives the same results and the same output order, which is the order of each user's first appearance.

I added `test_keeps_first_login_per_user` to `tests/test_events.py` to pin the first-login rule. Running `python -m unittest discover -s tests -t .` from the repo root gives 5 tests, all passing.

Suggestion: add a comment at the top of `one_login_per_user` or in `export.py` saying that first-wins is required by the trial clock, so a future cleanup doesn't flip it.
