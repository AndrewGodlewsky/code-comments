I retired docs/accounts.md and moved its rules next to the code they describe.

What moved where:
- Whitespace rule ("spaces before or after a name are ignored"): comment on `normalise_name` in `accounts/names.py`. The code does this, and the existing tests cover it.
- `register()` raises `NameTaken` when the name is in use: docstring on `Directory.register` in `accounts/users.py`.
- New accounts get `member`: docstring on `Directory.register`, tied to `DEFAULT_ROLE`.
- Only admins can grant `editor`, after the March 2025 spam wave (ACC-30): comment in `Directory.grant_role`. The code does this, and the existing tests cover it.

One rule did not move as written. The old page said usernames are case-insensitive (ACC-12) and that `find_user("Ann")` and `find_user("ann")` are the same account. The code does not do this: `normalise_name` only strips whitespace, so "Ann" and "ann" are two different accounts. I did not put the false claim into a comment as if it were true. The comment on `normalise_name` now says case-insensitivity is intended (ACC-12) but not implemented yet. Someone needs to decide whether to implement it (a code change) or drop the rule. I did not change behaviour in this task.

Nothing left on the page needs a standalone document, so I deleted docs/accounts.md. docs/support.md is unchanged. Its one line (password resets belong to the identity team) is a pointer to another service, not an account rule, and it stays where it is. README.md did not link to the deleted page, so I left it alone.

Files changed:
- accounts/names.py (comment added)
- accounts/users.py (docstring on `register`, comment in `grant_role`)
- docs/accounts.md (deleted)
- RESPONSE.md (this message)

I did not run the tests. The edits are comments and docstrings only.
