I simplified `one_login_per_user` in `accounts/events.py`, but I did not use the last-wins one-liner like `last_devices`. It keeps each user's first login.

Your "any login will do" is true for `reports/weekly.py`, which only counts users. It is not true for `accounts/export.py`. That function writes the `user_logins` table, and `billing/trial_clock.sql` says the row must be the user's FIRST login, because it starts the 14-day trial clock. A last-wins version would pass the current tests, which only check the user names. It would move trial start dates to each user's latest login.

New version:

```python
first = {}
for event in events:
    first.setdefault(event["user"], event)
return list(first.values())
```

Behaviour is the same as before: first login per user, in order of first appearance. It is a single pass instead of the reversed loop plus the `not in ordered` list scan, which was quadratic. The existing tests pass.

I did not add a test for the "first login" guarantee. I would suggest adding one, since nothing in the tests currently protects it. I also added a note to the docstring saying it keeps the first login.
