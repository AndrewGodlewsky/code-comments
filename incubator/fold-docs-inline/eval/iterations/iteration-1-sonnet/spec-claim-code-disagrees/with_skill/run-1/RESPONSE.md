I retired `docs/accounts.md` and deleted it. One comment was added, and one claim needs your decision.

**Fate list**

1. "Usernames are case-insensitive (ACC-12)": **not migrated.** `normalise_name` in `accounts/names.py` only calls `strip()`, so it does not lowercase. `find_user("Ann")` and `find_user("ann")` find different accounts, and `register()` accepts both. No test covers case.
2. "`find_user("Ann")` and `find_user("ann")` find the same account": **not migrated.** Same evidence as claim 1. `find_user` looks the name up in `_accounts` after `normalise_name`, which only strips.
3. "`register()` treats them as the same name": **not migrated.** `Directory.register` stores `"Ann"` and `"ann"` as separate keys.
4. "Spaces before or after a name are ignored": **dropped.** `normalise_name` strips, and `test_register_and_find` registers `" kim "` and finds `"kim"`.
5. "`register()` raises `NameTaken` when the name is already in use": **dropped.** `Directory.register` raises it, the `NameTaken` docstring says so, and `test_a_name_can_only_be_taken_once` covers it.
6. "New accounts get the `member` role": **dropped.** `DEFAULT_ROLE = "member"` is used in `register`, and `test_register_and_find` asserts it.
7. "Only an admin can grant `editor`": **dropped.** `Directory.grant_role` raises `PermissionError("only an admin can grant the editor role")`, and `test_only_admins_grant_editor` covers it.
8. "Editor rights were limited to admins after the spam wave in March 2025 (ACC-30)": **moved.** It is now a comment at the top of `Directory.grant_role` in `accounts/users.py`: "Editor rights are admin-only since the March 2025 spam wave (ACC-30)."

**Needs your call (claims 1-3):** which side is right, the page or the code? If usernames should be case-insensitive, `normalise_name` needs to lowercase, and I have not changed any code. If the code is right, ACC-12 may need revisiting. I left this out of the comments, and it is gone with the deleted page, so keep this list if you need it.

**Other files stating a moved fact:** none found.

**Links to the page:** none. README.md and docs/support.md do not link to `docs/accounts.md`.

**Gaps:** none.

**Page status:** `docs/accounts.md` is deleted, because no kept claim remained. `docs/support.md` is untouched.
