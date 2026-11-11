I simplified `one_login_per_user` in `accounts/events.py`. It now builds a dict with `setdefault` over the events in stream order and returns its values. The old two-pass version with the `reversed` loop and the `kept not in ordered` list scan is gone.

One thing to check before you rely on the "either login is fine" premise: it does not hold for `accounts/activation.py`. `activation_dates` uses `one_login_per_user` to set each user's activation date and trial clock, and its comment says later logins must not move it. So the function has to keep each user's first login, not an arbitrary one. The new version keeps the first login, which matches the old behaviour exactly, so `activation_dates`, `trial_ends` and `reports/weekly.py` are unaffected. I also rewrote the docstring to say this so the dependency is visible.

Output is unchanged: one event per user, the first one recorded, ordered by when each user first logged in. The existing tests in `tests/test_events.py` pass (4 tests). I also checked a small stream by hand and an empty list. I did not change `activation.py`, `sessions.py` or the tests.

If you actually want a different login kept, for example the latest, `activation_dates` would need to stop using this helper, because it would move the activation date.
