I retired `docs/accounts.md`. One claim is not migrated because the code contradicts it, so please decide which side is right before anything else changes.

**Fate list (page order)**

1. "Usernames are case-insensitive (ACC-12): `find_user("Ann")` and `find_user("ann")` find the same account, and `register()` treats them as the same name." — **Not migrated.** `accounts/names.py` `normalise_name` only calls `name.strip()`, with no lowering. `accounts/users.py` `find_user` and `register` look up the stripped key directly, so `"Ann"` and `"ann"` are different accounts. No comment added.
2. "Spaces before or after a name are ignored." — **Dropped.** The code states it: `accounts/names.py` `normalise_name` returns `name.strip()`.
3. "`register()` raises `NameTaken` when the name is already in use." — **Dropped.** The code states it: `accounts/users.py` `Directory.register` raises `NameTaken` when the key is already present.
4. "New accounts get the `member` role." — **Dropped.** The code states it: `accounts/users.py` `DEFAULT_ROLE = "member"`, used in `register`.
5. "Only an admin can grant `editor`." — **Dropped.** The code states it: `accounts/users.py` `Directory.grant_role` raises `PermissionError` unless `actor["role"] == "admin"`.
6. "editor rights were limited to admins after the spam wave in March 2025 (ACC-30)." — **Moved** to `accounts/users.py`, `Directory.grant_role`, as a comment above the editor check. This is a reason the code cannot show. It is a judgment call: it could also be read as decision history, which would keep it in a document. If you want that, I can restore `docs/accounts.md` with only this sentence.

**Changes made**
- `accounts/users.py`: added the two-line comment above `if role == "editor" and actor["role"] != "admin":` (fate 6). No code changed.
- `docs/accounts.md`: deleted. No kept claim remained, and you asked for retirement.
- `docs/support.md`, `README.md`, `accounts/__init__.py`, `accounts/names.py` and the tests are unchanged.

**Follow-up for you**
- The case-insensitivity rule (ACC-12) is no longer documented anywhere. The code does not implement it, so the page had a false claim. Either implement it, which is a code change I did not make, or confirm the rule is dropped. The text is preserved here in fate 1.
- No other file states the moved fact. No file links to `docs/accounts.md`.
- Gap: the code has no test for case-insensitivity, so the contradiction is not caught by the suite.
