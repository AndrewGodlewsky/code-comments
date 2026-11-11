I retired `docs/accounts.md` and moved its content into comments next to the code. One of its claims turned out to be false, so please read the second paragraph.

**Moved into comments**
- `accounts/users.py`: a comment on `DEFAULT_ROLE`, one on `register()` saying it raises `NameTaken`, and one on `grant_role()` giving the reason editor rights are admin-only (the March 2025 spam wave, ACC-30).
- `accounts/names.py`: a comment saying surrounding spaces are ignored.

**Where the page disagreed with the code**
The page said usernames are case-insensitive (ACC-12). `normalise_name()` only strips whitespace and never folds case, so `find_user("Ann")` and `find_user("ann")` find different accounts, and `register()` accepts both. I did not copy the false claim into a comment. The comment in `names.py` states what the code does today and notes that ACC-12 asks for case-insensitivity. I did not change the behaviour, since that was outside this request. The likely fix is lowercasing in `normalise_name()`, and you may want a ticket for it.

**Deleted**
`docs/accounts.md` is gone. Nothing on it needed a standalone document, and nothing else linked to it. `docs/support.md` (password resets belong to the identity team) is unrelated and untouched. I did not run the tests.
