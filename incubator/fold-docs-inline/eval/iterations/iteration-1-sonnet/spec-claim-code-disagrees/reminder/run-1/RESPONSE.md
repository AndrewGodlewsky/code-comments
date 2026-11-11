I retired docs/accounts.md. I moved one fact into a comment, left out three claims the code already shows, and held back one claim the code contradicts. The page is deleted because nothing left on it needed a document.

**Moved into a comment**
- The reason editor rights are admin-only (the March 2025 spam wave, ACC-30) is now a comment in `accounts/users.py`, directly above the admin check in `grant_role`. The code shows the rule but not why it exists.

**Left out because the code already shows it**
- Leading and trailing spaces in a name are ignored (`normalise_name` strips them).
- `register()` raises `NameTaken` for a name already in use (the code and its docstring say so).
- New accounts get the `member` role, and only an admin can grant `editor` (`DEFAULT_ROLE` and the check in `grant_role`).

**Not carried over because the code contradicts it**
- The page said usernames are case-insensitive (ACC-12), so `find_user("Ann")` and `find_user("ann")` find the same account. `normalise_name` only strips whitespace and never lowercases, so `"Ann"` and `"ann"` are different accounts. `register()` accepts both, and `find_user("Ann")` won't find `"ann"`. Either the page is out of date or the ACC-12 behaviour was never implemented. I didn't change any code, so you'll need to decide which. If case-insensitivity is intended, it needs a fix in `accounts/names.py` and a test.

**Other notes**
- I kept `docs/support.md`. It's about password resets, which belong to the identity team and have no code here to sit beside.
- No other file linked to `docs/accounts.md`, so nothing needed updating.
- The only other change is the one comment in `accounts/users.py`. I created no new files besides this message.
