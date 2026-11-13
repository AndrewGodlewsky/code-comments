I deleted docs/accounts.md and moved its content into comments next to the code, but one claim on that page is false, so I did not copy it over as written.

The page said usernames are case-insensitive (ACC-12), so `find_user("Ann")` and `find_user("ann")` would find the same account. The code does not do that. `normalise_name` in accounts/names.py only strips spaces, so "Ann" and "ann" are different accounts. No test covers this either way. I left the behaviour alone and put a comment in `normalise_name` saying case is not folded, that ACC-12 asks for it, and that the gap is unresolved. You need to decide whether to fold case (a one-line `.lower()` plus a test) or drop the ACC-12 requirement. I did not run the tests.

Where the rest went:
- Spaces around a name are ignored: comment in `normalise_name` (accounts/names.py).
- `register()` raises `NameTaken`: already covered by the `NameTaken` docstring and a test, so I added nothing.
- New accounts get `member`: comment on `DEFAULT_ROLE` (accounts/users.py).
- Only an admin can grant `editor`, with the March 2025 spam-wave reason (ACC-30): comment in `grant_role` (accounts/users.py).

Nothing on the page still needed a document, so I deleted it. Nothing linked to it. docs/support.md is unrelated and untouched.
