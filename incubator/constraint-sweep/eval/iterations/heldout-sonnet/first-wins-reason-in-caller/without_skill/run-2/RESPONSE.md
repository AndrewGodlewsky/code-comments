I simplified `one_login_per_user` in `accounts/events.py`, but I did not make it the `last_devices`-style one-liner you suggested. It matters which login it keeps, so it now keeps each user's first login.

`billing/trial_clock.sql` reads the `user_logins` table that `accounts/export.py` fills from this function. It treats each row as the user's activation date and starts the 14-day trial clock from it. Its comment says the row must be the user's FIRST login. A dict comprehension like `last_devices` keeps the last one, which would push trial end dates later on every nightly rebuild.

The old code did keep the first login, despite the `latest_seen` name. Its reversed loop let the earliest event overwrite the later ones. The new version says so directly:

```python
first = {}
for event in events:
    first.setdefault(event["user"], event)
return list(first.values())
```

It returns the same events in the same order as before. The docstring now says "first login". The weekly report only counts users, so it is not affected either way.

I added `test_keeps_first_login` to `tests/test_events.py` so a change to the last login fails a test. The test suite passes.
