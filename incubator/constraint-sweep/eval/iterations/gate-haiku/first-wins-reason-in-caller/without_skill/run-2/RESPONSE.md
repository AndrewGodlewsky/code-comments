I simplified `one_login_per_user` in `accounts/events.py`, but it still keeps each user's first login, not an arbitrary one. The old version also did this; the reversed loop only looked clumsy.

The reason is `accounts/activation.py`. Its `activation_dates` uses `one_login_per_user` to get each account's activation date, and the comment there says the first login starts the 14-day trial clock and later logins must not move it. If the function kept an arbitrary login, `trial_ends` would move with it. `reports/weekly.py` only counts users, so it doesn't care which login is kept, but the function is shared.

The new version is:

```python
def one_login_per_user(events):
    """Return each user's first login event, ordered by each user's first appearance."""
    first_by_user = {}
    for event in events:
        first_by_user.setdefault(event["user"], event)
    return list(first_by_user.values())
```

It returns the same events in the same order as before, and it runs in linear time instead of quadratic. The `kept not in ordered` check is gone. All 4 existing tests pass, and a quick check on a sample stream returned the first login for each user (ana at 9, ben at 10).

I did not add a test that pins first-wins, though one would protect the trial clock. Say if you want one.
