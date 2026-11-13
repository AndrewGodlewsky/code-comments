I retired docs/accounts.md. Its rules now sit next to the code, and the page is deleted. docs/support.md is untouched.

What moved:

- Spaces before and after a name are ignored. This is now the docstring of `normalise_name` in `accounts/names.py`.
- Editor rights are admin-only, with the reason (the March 2025 spam wave, ACC-30). This is a comment above the check in `grant_role` in `accounts/users.py`.
- `register()` raising `NameTaken` and new accounts getting `member` were not moved. The code and the existing `NameTaken` docstring already say both, so a comment would only restate them.

One claim does not match the code, and you need to decide it:

- The doc says usernames are case-insensitive (ACC-12). The code does not do this. `normalise_name` only strips whitespace, so "Ann" and "ann" are separate accounts. I did not write "case-insensitive" as a fact in any comment. I put a TODO(ACC-12) on `normalise_name` that states the intent and the current behaviour. Either the code needs case folding, or ACC-12 is stale and the TODO should go. I could not check ACC-12 itself, and I did not use the tracker.

Also worth a look, not changed: `grant_role` only guards the `editor` role. Any actor, including a member, can set another account to `admin` or to any other string. The docs do not promise otherwise, so I left the behaviour and the comments alone.
