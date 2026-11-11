I simplified `one_login_per_user` in `accounts/events.py`, but it keeps each user's first login, not an arbitrary one, so it is not the last-wins one-liner that `last_devices` uses. The tests pass.

Why first: `billing/trial_clock.sql:2-5` says the `user_logins` row written by `accounts/export.py` from this function "must be the user's FIRST login". That row is the activation date and starts the 14-day trial. Nothing between the function and the SQL enforces this, so a last-wins version would silently push trial dates later. The old code was first-wins as well, just roundabout.

The new body is a short loop using `dict.setdefault`, returning `list(first.values())`. This gives the same results as before, including ordering by each user's first appearance. I also updated the docstring to say it keeps the first login and why. The old one only said "one login per user", which hid this requirement.

`reports/weekly.py` only counts users, so it is unaffected. No tests pin the first-login property. A test that checks which login is returned would be worth adding, but I left that for you to decide.
