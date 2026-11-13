I did not delete `docs/accounts.md`. One claim on it conflicts with the code, so the page still has to stand until someone decides it.

**Moved into code (docstrings):**
- `accounts/names.py`, `normalise_name`: strips surrounding whitespace; registration and lookup both use it; otherwise matching is case-sensitive.
- `accounts/users.py`, `Directory.register`: creates the account with `DEFAULT_ROLE` (`member`); raises `NameTaken` when the normalised name is taken.
- `accounts/users.py`, `Directory.grant_role`: only an admin may grant `editor`, a limit added after the March 2025 spam wave (ACC-30).

**Kept in `docs/accounts.md`, unresolved:**
- The page says usernames are case-insensitive (ACC-12), so `find_user("Ann")` and `find_user("ann")` should find the same account. The code does not do this: `normalise_name` only strips whitespace, and no test covers case. I did not write this into a code comment because the code contradicts it and I cannot tell from here whether ACC-12 still stands. Please decide: implement it, or drop the claim and delete the page.

**Not changed:**
- `docs/support.md` is a separate page and was left alone.
- No tests were added.

**Observation outside this task:** `grant_role` only restricts `editor`. A non-admin actor can still set any other role, including `admin`. This matches the page's wording, but it may be worth a check.
