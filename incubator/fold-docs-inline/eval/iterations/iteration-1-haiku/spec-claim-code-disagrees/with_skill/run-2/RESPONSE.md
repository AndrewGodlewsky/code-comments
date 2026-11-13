I folded docs/accounts.md into the code and deleted the page. One claim conflicts with the code, so please decide which side is right.

Fate list, in page order:

1. "Usernames are case-insensitive (ACC-12)". Not migrated. accounts/names.py `normalise_name` only calls `strip()`, so names are case-sensitive. I put no comment here and removed the claim from the page.
2. "find_user("Ann") and find_user("ann") find the same account". Not migrated. accounts/users.py `find_user` looks up `normalise_name(name)` with no case folding, so `find_user("Ann")` returns None when "ann" is registered.
3. "register() treats them as the same name". Not migrated. accounts/users.py `register` checks `key in self._accounts` on the case-sensitive key, so "Ann" and "ann" can both be registered.
4. "Spaces before or after a name are ignored". Dropped. `normalise_name` in accounts/names.py calls `strip()`, and tests/test_users.py `test_register_and_find` registers " kim " and finds "kim".
5. "register() raises NameTaken when the name is already in use". Dropped. accounts/users.py `register` raises `NameTaken`, whose class docstring states the rule, and tests/test_users.py `test_a_name_can_only_be_taken_once` covers it.
6. "New accounts get the member role". Dropped. accounts/users.py `DEFAULT_ROLE = "member"` is used in `register`, and tests/test_users.py asserts the role is "member".
7. "Only an admin can grant editor". Dropped. accounts/users.py `grant_role` raises PermissionError unless the actor is admin, and tests/test_users.py `test_only_admins_grant_editor` covers it.
8. "editor rights were limited to admins after the spam wave in March 2025 (ACC-30)". Moved to the docstring of accounts/users.py `Directory.grant_role`. The code cannot show why the editor check exists, so the reason now sits beside it, with ACC-30 kept. This is decision history, which the skill would normally keep in a document. I moved it because it explains the check a later editor might try to relax. If you want it in a document instead, tell me and I will restore it.

What changed:
- accounts/users.py: added the docstring to `grant_role`. No other code changed.
- docs/accounts.md: deleted. No kept claim remained.
- docs/support.md, README.md, tests/, and the other accounts/ files are unchanged.

Items for you to decide or fill:
- The case-insensitivity claim (ACC-12) conflicts with the code. Either the code should fold case as ACC-12 intended, or the claim is stale. Deleting the page removed the claim from the repository. If the repo keeps history, the old text is still there.
- No other file states the moved fact, and no file links to docs/accounts.md. The README is a single line, so it has no overview to keep.
