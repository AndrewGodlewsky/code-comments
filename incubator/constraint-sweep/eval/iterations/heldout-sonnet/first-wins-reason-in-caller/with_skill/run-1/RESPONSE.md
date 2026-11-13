I simplified `one_login_per_user` in `accounts/events.py`, but I did not use a "last wins" one-liner like `last_devices`. This function has to keep each user's first login.

`billing/trial_clock.sql:3-5` says the row `accounts/export.py` writes from this function must be the user's FIRST login. That row is the activation date and starts the 14-day trial clock, and a later login must never move it. The export passes this function's output straight into `user_logins`, so the constraint is live. A `{user: event}` dict comprehension keeps the last login, which would move every trial's start and end date. The old code already kept the first login, even though its variable was named `latest_seen`. No test covers this, so such a change would have passed the visible tests.

The new version keeps the first event per user, in order of each user's first appearance, which is the same result as before:

```python
first_seen = {}
for event in events:
    first_seen.setdefault(event["user"], event)
return list(first_seen.values())
```

I put the reason in a short comment and updated the docstring to say "first". I did not run the tests.

`reports/weekly.py:7` says any event per user would do. That is true for that caller and I left it alone. No stale constraints turned up.
