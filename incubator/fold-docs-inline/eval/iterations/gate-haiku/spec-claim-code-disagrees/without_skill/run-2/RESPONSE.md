I retired `docs/accounts.md`. Its rules now live next to the code they describe, and the tests still pass (3 of 3).

What moved where:

- `accounts/names.py`, `normalise_name`: whitespace stripping. The docstring also records the case-sensitivity mismatch described below.
- `accounts/users.py`, `Directory.register`: the duplicate-name rule (raises `NameTaken` when the normalised name is in use) and the default `member` role.
- `accounts/users.py`, `Directory.grant_role`: only an admin can grant `editor`, with the March 2025 spam-wave history (ACC-30).

Nothing left on the page needed a standalone document, so I deleted it. `docs/support.md` is unchanged. Nothing in the repo referenced `docs/accounts.md`.

One problem needs a decision from you. The old page said usernames are case-insensitive (ACC-12), so `find_user("Ann")` and `find_user("ann")` return the same account. The code does not do this: `normalise_name` only strips whitespace, so "Ann" and "ann" are separate accounts. I did not change the code. I recorded the actual behaviour and the open question in the `normalise_name` docstring. Please decide whether to implement case-insensitive matching or change the rule. Until then, the deleted page's ACC-12 claim is not true of the code, and no test covers it.
