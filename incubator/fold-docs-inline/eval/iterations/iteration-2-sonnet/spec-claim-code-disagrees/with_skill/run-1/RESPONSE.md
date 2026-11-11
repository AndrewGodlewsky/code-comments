I folded docs/accounts.md into the code and deleted it. One claim on it disagrees with the code, and I need you to say which side is right.

Fate list, in page order:

1. "Usernames are case-insensitive (ACC-12)": not migrated. `normalise_name` in accounts/names.py only calls `.strip()`, with no case folding. `find_user("Ann")` and `find_user("ann")` therefore look up different keys, and `register()` treats them as different names. No test covers case.
2. "`find_user("Ann")` and `find_user("ann")` find the same account": not migrated, same evidence. Today `find_user("Ann")` returns None after `register("ann")`.
3. "`register()` treats them as the same name": not migrated, same evidence. `register("Ann")` after `register("ann")` succeeds.
4. "Spaces before or after a name are ignored": dropped. `normalise_name` strips, and `test_register_and_find` registers " kim ".
5. "`register()` raises `NameTaken` when the name is already in use": dropped. `Directory.register` and the `NameTaken` docstring state it, and `test_a_name_can_only_be_taken_once` covers it.
6. "New accounts get the `member` role": dropped. `DEFAULT_ROLE = "member"` in accounts/users.py, and `test_register_and_find` checks it.
7. "Only an admin can grant `editor`": dropped. The check in `Directory.grant_role` and its error message state it, and `test_only_admins_grant_editor` covers it.
8. "Editor rights were limited to admins after the spam wave in March 2025 (ACC-30)": moved. It is now a comment above the admin check in `Directory.grant_role` in accounts/users.py, with the ticket id kept.

Decision for you: ACC-12 says names are case-insensitive, but the code is case-sensitive. I changed no code and wrote nothing about case into any comment. Either the code should fold case (then the ACC-12 claim returns once it is true) or the requirement was dropped. Because the page is deleted, the ACC-12 claim now survives only in this reply. If you want it kept as a record until you decide, restore the page with just that bullet.

Other files:
- No other file states the moved ACC-30 fact.
- No file links to docs/accounts.md. README.md does not mention it.
- docs/support.md is untouched.
- Gaps: none.

docs/accounts.md is deleted, since no claim remained that needed a document.
