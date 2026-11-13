I retired docs/accounts.md. Before moving anything, I checked each claim against the code.

One claim is contradicted by the code, so I did not carry it over:

- The page says usernames are case-insensitive (ACC-12), so `find_user("Ann")` and `find_user("ann")` return the same account and `register()` treats them as one name. The code does not do this. `normalise_name` only strips whitespace (accounts/names.py), and the directory is keyed on that string, so "Ann" and "ann" are different keys. Both can be registered. The tests do not cover case at all. This needs a decision from you: either the code should lowercase names, or the requirement (ACC-12) is out of date.

The remaining claims were already shown by the code, so I left them off the page:

- Surrounding spaces are ignored: `normalise_name` strips.
- `register()` raises `NameTaken` for a name already in use.
- New accounts get the `member` role: `DEFAULT_ROLE`.
- Only an admin can grant `editor`: the check in `grant_role`, which the tests exercise.

One fact had no visible reason in the code: editor rights were limited to admins after the March 2025 spam wave (ACC-30). I put it in one comment beside the check in `grant_role` (accounts/users.py).

Nothing on the page was left without code to sit beside, so no document remains and I deleted docs/accounts.md. I did not change any code beyond that comment, and I created no new files other than this RESPONSE.md. docs/support.md is unchanged; it is about password resets and does not reference the accounts page.
