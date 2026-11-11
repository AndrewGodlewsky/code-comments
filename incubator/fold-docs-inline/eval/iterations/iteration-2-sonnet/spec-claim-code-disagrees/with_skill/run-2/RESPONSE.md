I retired docs/accounts.md and deleted it. One comment was added, in accounts/users.py. One claim on the page contradicts the code and I did not migrate it, so please read that one.

Fate list, in page order:

1. "Usernames are case-insensitive (ACC-12)": **Not migrated.** `accounts/names.py` `normalise_name` only does `name.strip()`, with no lowercasing. So `find_user("Ann")` and `find_user("ann")` find different accounts, and `register()` accepts both. The tests never exercise mixed case. Which side is right? If case-insensitivity is intended, the code needs fixing (I changed no code). If it is not, the ACC-12 note is stale. No comment states it, and the ACC-12 reference is gone from the repo with the page.
2. "`find_user("Ann")` and `find_user("ann")` find the same account": **Not migrated.** Same evidence as 1.
3. "`register()` treats them as the same name": **Not migrated.** `register` keys on `normalise_name(name)`, which is not case-folded, so "Ann" and "ann" can both register.
4. "Spaces before or after a name are ignored": **Dropped.** `normalise_name` in `accounts/names.py` strips them, and `test_register_and_find` registers `" kim "`.
5. "`register()` raises `NameTaken` when the name is already in use": **Dropped.** `Directory.register` in `accounts/users.py` raises it, the `NameTaken` docstring says so, and `test_a_name_can_only_be_taken_once` covers it.
6. "New accounts get the `member` role": **Dropped.** `DEFAULT_ROLE = "member"` and `register` in `accounts/users.py`, plus an assertion in `test_register_and_find`.
7. "Only an admin can grant `editor`": **Dropped.** `Directory.grant_role` enforces it, with the error message and `test_only_admins_grant_editor`.
8. "editor rights were limited to admins after the spam wave in March 2025 (ACC-30)": **Moved** to a comment in `accounts/users.py`, in `Directory.grant_role` above the admin check. It is the reason the code cannot show.

Other files that state a moved fact: none.
Files that link to the page: none. README.md and docs/support.md do not reference it.
Gaps: none. docs/support.md is unrelated, since it is about password resets, and I left it alone.
The page is deleted. Nothing on it needed a document.
