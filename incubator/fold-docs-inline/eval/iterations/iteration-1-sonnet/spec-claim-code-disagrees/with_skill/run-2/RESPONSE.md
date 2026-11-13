I folded docs/accounts.md into the code and deleted the page. One claim is not migrated because the code contradicts it, and I need your call on it.

**Fate list (page order)**

1. "Usernames are case-insensitive (ACC-12)": NOT MIGRATED. `normalise_name` in accounts/names.py only does `name.strip()`, with no case folding.
2. "`find_user("Ann")` and `find_user("ann")` find the same account": NOT MIGRATED. `Directory.find_user` looks up the stripped name only, so these are two different keys and "Ann" would not find "ann".
3. "`register()` treats them as the same name": NOT MIGRATED. `Directory.register` keys on `normalise_name(name)`, so "Ann" and "ann" can both register without `NameTaken`.
4. "Spaces before or after a name are ignored": DROPPED. `normalise_name` strips, and `test_register_and_find` registers `" kim "` and finds `"kim"`.
5. "`register()` raises `NameTaken` when the name is already in use": DROPPED. `register` raises it, the `NameTaken` docstring says so, and `test_a_name_can_only_be_taken_once` covers it.
6. "New accounts get the `member` role": DROPPED. `DEFAULT_ROLE = "member"` in accounts/users.py, and `test_register_and_find` asserts it.
7. "Only an admin can grant `editor`": DROPPED. `Directory.grant_role` raises `PermissionError("only an admin can grant the editor role")`, and `test_only_admins_grant_editor` covers it.
8. "Editor rights were limited to admins after the spam wave in March 2025 (ACC-30)": MOVED. It is now a comment in accounts/users.py at `Directory.grant_role`, above the editor check. The comment keeps ACC-30.

**Decision for you:** ACC-12 says names are case-insensitive, but the code is case-sensitive. I changed no code and wrote nothing about case into any comment. Which side is right? If the page is right, `normalise_name` needs case folding, and that is a code change for you or another task.

**Other files**
- Other files stating a moved fact: none.
- Links to docs/accounts.md: none found in README.md, docs/support.md or the code.
- Gaps: none.
- docs/accounts.md is deleted because no kept claim remained. docs/support.md is untouched.
