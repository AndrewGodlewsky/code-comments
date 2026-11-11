I retired `docs/accounts.md` and deleted it. `docs/support.md` is untouched, and nothing else linked to the deleted page.

Where each point went:
- **Spaces ignored:** a docstring on `normalise_name` in `accounts/names.py`, plus a note in the `register()` docstring.
- **`register()` raises `NameTaken`:** the `register()` docstring in `accounts/users.py`. The `member` default is already the `DEFAULT_ROLE` constant, so it needed no comment.
- **Only admins can grant `editor`, and why:** a comment above the check in `grant_role`, with the reason (the March 2025 spam wave) and ACC-30.

**Case-insensitivity not carried over.** The page said usernames are case-insensitive (ACC-12), but the code does not do that. `normalise_name` only strips spaces, so `find_user("Ann")` and `find_user("ann")` find different accounts, and `register()` accepts both. I did not put the claim in a comment, because it would be false. I also did not change the code, since you asked only for comments.

Deleting the page means that requirement is no longer written down anywhere. Either the code should fold case (then say so in `normalise_name`), or ACC-12 needs revisiting. Tell me which and I will do it.
