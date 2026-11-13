I simplified `one_login_per_user` in `accounts/events.py` from a two-pass dict-and-list loop to a short `setdefault` loop. Behaviour is unchanged: it still keeps each user's first login, in order of first login. Unit tests pass (5 of 5).

I did not use the `last_devices` one-liner shape, because it would keep the latest login, and that breaks billing. `billing/trial_clock.sql` says each `user_logins` row must be the user's first login, since it is the activation date and starts the 14-day trial clock. So which login is kept does matter here. The function's current shape was the only visible sign of this rule, so I wrote the rule and its reason into the docstring beside the code.

I also added `test_keeps_first_login` to `tests/test_events.py`. The existing tests did not check which login is kept, so nothing would have caught a switch to the latest login.

Two things to check:
- The output order is unchanged, but nothing in the repo depends on it. `export.py` inserts rows and the tests sort, so a different order would not break anything.
- The `setdefault` loop is four lines, not one. A true one-liner that keeps first-login order is awkward in Python. If you want one anyway, tell me and I will try a version.
