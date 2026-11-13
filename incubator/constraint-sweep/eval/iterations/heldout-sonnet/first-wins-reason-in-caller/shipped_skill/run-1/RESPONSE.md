I simplified `one_login_per_user` in `accounts/events.py` to a short loop with `setdefault`. It is not quite the one-liner you suggested, and I did not copy the `last_devices` pattern.

**The choice of login matters.** The old code keeps each user's first login, not an arbitrary one, and a one-line dict comprehension like `last_devices` would keep the last login. `accounts/export.py` writes these events into `user_logins`. `billing/trial_clock.sql` treats that row as the account's activation date and starts the 14-day trial clock from it. Its comment says it must be the first login and that a later login must never move it. If the last login were kept, trials would start later and run longer, and the invoices would go out later than they should.

**What I changed.**
- The new version keeps the first login per user and returns users in order of first login, as before.
- I put the "first login, and why" rule in the function's docstring, since the old code's shape was the only visible sign of it. The reason points at `accounts/export.py` and `billing/trial_clock.sql`.
- I ran the existing tests and they pass. They only check one event per user, not which one is kept, so nothing tests the first-login rule. A test for it would be worth adding.

**One comment I left alone.** `reports/weekly.py` says "any one event per user would do". That is true for the weekly count, and I did not change it. It may read as permission to change which login is kept, though, so you may want to reword it.
