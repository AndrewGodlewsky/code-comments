# docs/accounts.md retired

I deleted `docs/accounts.md`. Nothing on it stayed as a kept claim. I added one docstring to `accounts/users.py`, and no other file changed. Three of the page's claims contradict the code, so please review them before you rely on the retirement.

## Fate list (page order)

1. "Usernames are case-insensitive (ACC-12)". **Not migrated.** `accounts/names.py:4-5` `normalise_name` only calls `strip()`. It does not lowercase, so the code is case-sensitive.
2. "`find_user("Ann")` and `find_user("ann")` find the same account". **Not migrated.** `accounts/users.py:23-25` looks up the exact stripped key, so the two names are different keys.
3. "`register()` treats them as the same name". **Not migrated.** `accounts/users.py:16-19` checks for a duplicate on the stripped key only, so `register("Ann")` and then `register("ann")` both succeed.
4. "Spaces before or after a name are ignored." **Dropped.** `accounts/names.py:5` `name.strip()` states it. `tests/test_users.py:9-10` registers `" kim "` and finds `"kim"`.
5. "`register()` raises `NameTaken` when the name is already in use." **Dropped.** `accounts/users.py:18-19` states it. `tests/test_users.py:12-16` covers it.
6. "New accounts get the `member` role." **Dropped.** `accounts/users.py:5` `DEFAULT_ROLE = "member"` and line 20 state it. `tests/test_users.py:7-10` covers it.
7. "Only an admin can grant `editor`." **Dropped.** `accounts/users.py:29-30` raises `PermissionError` for non-admins. `tests/test_users.py:18-24` covers it.
8. "Editor rights were limited to admins after the spam wave in March 2025 (ACC-30)." **Moved** to the `Directory.grant_role` docstring, `accounts/users.py:27-31`, with the ticket id kept. The code cannot show why the admin check exists. This is a judgment call: the skill lists decision history as kept, so move this line back to the page if you would rather keep the history as a document.

## Changes

- `accounts/users.py`: added a docstring to `grant_role` (the fate 8 comment).
- `docs/accounts.md`: deleted. Its text is quoted in full above, so the claims survive in this file.

## Other files and gaps

- No other file states a moved fact, and no file links to `docs/accounts.md`. `README.md` and `docs/support.md` are unchanged.
- **Decision needed (claims 1-3):** the page says usernames are case-insensitive (ACC-12), but the code is case-sensitive. Please decide which side is right. If case-insensitivity is intended, the code needs a change, which I did not make. If it is not, the claim is wrong and the page is gone. Git history still has the text if you need it.
- The page had no module overview, so there was nothing to move to a module docstring.
