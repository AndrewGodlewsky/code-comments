I moved most of docs/accounts.md into code comments but could not delete the page, because one of its claims does not match the code.

Moved into comments (no logic changed):
- `accounts/names.py`: `normalise_name` docstring says leading and trailing spaces are removed and case is kept as given.
- `accounts/users.py`: `DEFAULT_ROLE` says it is the role every new account gets from `register()`.
- `accounts/users.py`: `register` docstring says it raises `NameTaken` when the normalised name is already in use.
- `accounts/users.py`: `grant_role` docstring says only an admin may grant `editor`, citing the March 2025 spam wave (ACC-30).

Not moved, and the page is kept:
- The case-insensitive username rule (ACC-12) is not implemented. `normalise_name` only strips spaces, so `find_user("Ann")` and `find_user("ann")` return different results, and `register("Ann")` and `register("ann")` create two accounts. I did not write this into a comment because it would describe behaviour the code does not have. `docs/accounts.md` now holds only this bullet.

Decision needed: either the code should fold case (a fix outside this comment-only pass), or the ACC-12 claim is stale and should be dropped. Once that is settled, `docs/accounts.md` can be deleted, or the rule can go in `users.py` if it is kept.

`docs/support.md` is unrelated to the code and is unchanged. Nothing was committed.
