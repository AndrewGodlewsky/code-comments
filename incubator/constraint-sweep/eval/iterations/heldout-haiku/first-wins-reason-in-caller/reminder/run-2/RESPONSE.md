I simplified `one_login_per_user` in `accounts/events.py`, but I did not use the `last_devices` pattern. It keeps the last login per user, and billing depends on the first one.

`billing/trial_clock.sql` says the `user_logins` row must be each user's first login. It is the activation date and starts the 14-day trial clock, and a later login must never move it. `accounts/export.py` fills `user_logins` from `one_login_per_user`, so the function has to keep the first event per user. The current code does that, and a `last_devices`-style rewrite would quietly move every trial clock to the latest login.

The new version is a single pass with `setdefault`:

```python
def one_login_per_user(events):
    first_seen = {}
    for event in events:
        first_seen.setdefault(event["user"], event)
    return list(first_seen.values())
```

What is preserved:
- The first login per user is kept, as before.
- Results come out in order of each user's first appearance, as before. Sample check: `ana@9, ben@10, ana@11, cy@12, ben@13` gives `ana@9, ben@10, cy@12` with the original and the new code.

What changed:
- The docstring now states that the first login is kept and points to `billing/trial_clock.sql`, so the constraint lives next to the code.
- I added `test_keeps_first_login_per_user` in `tests/test_events.py`. The existing tests only checked which users came back, not which login. All 5 tests pass.

Other callers, checked with a grep across every file type:
- `accounts/export.py` and `reports/weekly.py` use only the count or the user/at/device fields, and their behaviour is unchanged.
- `billing/trial_clock.sql` is the constraint described above. I did not change it.
- `docs/trial.md` and `README.md` do not mention this function.

If you do want a different login kept, for example the latest, that is a billing change first: `trial_clock.sql` would need a new activation rule, not just a different row.
