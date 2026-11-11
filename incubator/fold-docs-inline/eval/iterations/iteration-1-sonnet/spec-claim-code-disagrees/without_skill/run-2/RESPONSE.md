I retired docs/accounts.md and deleted it. Nothing on it needed a document, and nothing else linked to it. docs/support.md is untouched.

One claim on the page was wrong, so I did not move it into a comment. The page said usernames are case-insensitive (ACC-12), so `find_user("Ann")` and `find_user("ann")` find the same account. The code doesn't do that. `normalise_name` only calls `strip()`, so "Ann" and "ann" are different accounts. I recorded the actual behaviour as a comment in `accounts/names.py`. I did not change any code. If ACC-12 is meant to hold, `normalise_name` needs a `.lower()` and a test. Either the code or the ticket is out of date, and I can't tell which from here.

What moved into comments:
- `accounts/names.py`: only surrounding whitespace is removed, and case is preserved. This covers the "spaces are ignored" line.
- `accounts/users.py`, `register()`: a docstring saying it creates an account with the default role, raises `NameTaken` when the name is in use, and compares names after normalising.
- `accounts/users.py`, `grant_role()`: only an admin can grant editor, with the reason (the March 2025 spam wave, ACC-30).

I didn't add a comment for the `member` default role, because `DEFAULT_ROLE` already says it.

I did not run the tests.
