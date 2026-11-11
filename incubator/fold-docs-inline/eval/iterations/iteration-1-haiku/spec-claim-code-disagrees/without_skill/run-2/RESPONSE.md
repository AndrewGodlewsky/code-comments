I moved the account rules from docs/accounts.md into the code and deleted the page. docs/support.md stays, since it has nothing to do with accounts and still needs a document.

What moved, and where:

- Whitespace is ignored around names. This is now a comment on `normalise_name` in `accounts/names.py`.
- `register()` raises `NameTaken` when the name is in use. This is now the docstring of `Directory.register` in `accounts/users.py`. The existing test already covers it.
- New accounts get the `member` role. This is now a comment above `DEFAULT_ROLE` in `accounts/users.py`.
- Only an admin can grant `editor`, a rule tightened after the March 2025 spam wave (ACC-30). This is also a comment above `DEFAULT_ROLE`. The existing test covers it.

One claim did not move as written. docs/accounts.md says usernames are case-insensitive (ACC-12), and that `find_user("Ann")` and `find_user("ann")` return the same account. The code does not do this. `normalise_name` only strips whitespace, so "Ann" and "ann" are two different accounts. I did not copy the claim into a comment as fact. Instead, the comment on `normalise_name` states the current behaviour and says that ACC-12 is not implemented, with a TODO to decide on it and then fold case and add a test.

Decision for you: ACC-12 is still an open requirement, and the TODO comment is now its only record in the repository. If you want it tracked elsewhere, that is the place to file it. Otherwise, confirm whether case-insensitive usernames are still wanted, and I will implement and test them.

Verification: `python -m unittest discover -s tests -t .` runs 3 tests, all passing. I changed only comments and docstrings in the code, so behaviour is unchanged.
