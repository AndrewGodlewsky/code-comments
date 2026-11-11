I simplified `one_login_per_user` in `accounts/events.py`, but not to the "keep any one login" version you suggested. It has to keep each user's first login.

`billing/trial_clock.sql` says the row that `export_user_logins` writes from `one_login_per_user` must be the user's first login. It sets `activated_at` and starts the 14-day trial clock, and a later login must never move it. So a `last_devices`-style version, which keeps the latest event, would silently restart trials for returning users.

The function now is:

```python
def one_login_per_user(events):
    first = {}
    for event in events:
        first.setdefault(event["user"], event)
    return list(first.values())
```

I checked that the output is the same as before: first login per user, ordered by when each user first appears in the stream. The docstring now records the first-login constraint and points at the SQL file.

I also added `test_keeps_first_login_per_user` to `tests/test_events.py`. Nothing tested which login was kept, so the constraint was unguarded. All 5 tests pass (`python -m unittest discover -s tests -t .`).

What I grepped: every file in the repo, including the SQL, docs and README. The constraints I found:
- `billing/trial_clock.sql`: first login required (the one that matters here).
- `accounts/sessions.py`: its docstring says every login counts, unlike `one_login_per_user`. Unchanged.
- `reports/weekly.py`: only needs the count of users, so any one event per user is fine. Unchanged.
- `accounts/export.py`: writes one row per user into `user_logins`, which has `user` as primary key. Unchanged.
- `docs/trial.md`: says only that a trial is 14 days. Nothing about which login counts.

Decision for you: if billing wants trials to start from the most recent login, that is a change to `billing/trial_clock.sql` and this function would be the simple version. I left the first-login behaviour in place because the SQL file currently depends on it.
