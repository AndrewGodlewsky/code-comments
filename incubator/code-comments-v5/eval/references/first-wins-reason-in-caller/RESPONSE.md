I simplified `one_login_per_user` to a single pass with `dict.setdefault`. It keeps the same behaviour as before: each user's first event, in the order users first appear.

I didn't copy `last_devices`, because which login it keeps does matter. `accounts/export.py` writes this function's result to the `user_logins` table, and `billing/trial_clock.sql` reads that table as each account's activation date. Its comment says the row must be the user's first login, because it starts the 14-day trial clock and a later login must never move it. The old loop walked the events in reverse and overwrote, so it kept the first event despite the `latest_seen` name. A last-wins one-liner would have passed the current tests, which only check one event per user, and pushed back the trial end of every user who logged in again.

I added a one-line comment saying the first event wins and why. The tests pass.
