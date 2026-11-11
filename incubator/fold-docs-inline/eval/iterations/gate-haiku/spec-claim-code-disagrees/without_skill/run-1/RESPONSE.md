I retired docs/accounts.md. Its rules now live next to the code, and I deleted the page because nothing on it needs a separate document.

What moved where:
- Whitespace trimming (`normalise_name`) is documented in the docstring of `accounts/names.py`.
- `NameTaken` on duplicate names is documented in the `register()` docstring in `accounts/users.py`.
- The `member` default role is commented on `DEFAULT_ROLE`, and the editor restriction and its March 2025 reason (ACC-30) are in the `grant_role()` docstring.

One claim did not move as written. The page says usernames are case-insensitive (ACC-12), but `normalise_name` only strips whitespace, so `find_user("Ann")` does not find an account registered as "ann". The docstring now states the actual behaviour and marks ACC-12 as open. This needs a decision: either fold case in `normalise_name`, or change the ACC-12 requirement. Adding a test for case-insensitivity would also expose the gap, since none exists today.

The existing tests pass (3 run, OK). I did not change any behaviour, only docstrings and comments, and I left docs/support.md in place.
