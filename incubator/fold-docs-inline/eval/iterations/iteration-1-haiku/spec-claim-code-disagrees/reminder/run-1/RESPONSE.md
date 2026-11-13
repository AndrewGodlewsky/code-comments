I retired docs/accounts.md. Before moving anything, I checked each claim against the code.

Checked against the code:

- Spaces before or after a name are ignored. `normalise_name` strips whitespace and every lookup goes through it, so the code already shows this. Left out.
- `register()` raises `NameTaken` when the name is taken. Shown in `Directory.register`. Left out.
- New accounts get the `member` role. Shown by `DEFAULT_ROLE`. Left out.
- Only an admin can grant `editor`. Shown by the check in `grant_role`. Left out.
- Editor rights were limited to admins after the March 2025 spam wave (ACC-30). The code does not show why, so I moved it into a comment beside the check in `accounts/users.py` (`grant_role`).

Contradicted by the code, so I did not carry it over:

- "Usernames are case-insensitive (ACC-12): `find_user("Ann")` and `find_user("ann")` find the same account, and `register()` treats them as the same name." This is false. `normalise_name` only calls `strip()`, and the accounts dict is keyed by the exact string. `find_user("Ann")` and `find_user("ann")` return different results, and `register("Ann")` followed by `register("ann")` succeeds and creates two accounts. Either the code is missing case folding or the claim is stale. This needs a decision from you. If case-insensitivity is intended, it is a code change, which I did not make.

Nothing on the page still needs a document, so I deleted docs/accounts.md. Nothing else in the repo referenced it. docs/support.md is unchanged. Its one claim, that password resets belong to the identity team, has no code to sit beside, but it is on a separate page and was outside this retirement.

Changes:

- `accounts/users.py`: one comment added above the editor check in `grant_role`. No code was changed, and no files were created.
- `docs/accounts.md`: deleted.
