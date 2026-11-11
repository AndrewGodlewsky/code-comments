I simplified `one_login_per_user` in `accounts/events.py` to a `setdefault` loop over a dict, returning `list(first_seen.values())`. It is now 4 lines instead of 9.

You said it doesn't matter which login is kept, but it does matter in this repo. `accounts/activation.py` uses these events as each user's activation time and relies on the function keeping each user's first login. So I kept the first login per user, and the result is still in order of each user's first appearance. Behaviour is unchanged, and the tests pass.

If you do want a different login kept, `activation.py` would need to change as well.
