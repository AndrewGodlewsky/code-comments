I've retired docs/accounts.md. Claim by claim:

- **Usernames are case-insensitive (ACC-12).** Not moved, because the code doesn't do this. Every lookup goes through `normalise_name()` in accounts/names.py, which only strips spaces, so `find_user("Ann")` does not find an account registered as "ann", and `register()` accepts both as different names. I didn't change the lookup: making names case-insensitive would merge or block existing accounts, so it needs your decision. Either ACC-12 was never finished, or the page is wrong. Tell me which and I'll make the change separately if you want it.
- **Spaces around a name are ignored.** Dropped: `normalise_name()` is `name.strip()`.
- **`register()` raises `NameTaken` for a name already in use.** Dropped: the code and the exception's docstring show it.
- **New accounts get `member`; only admins grant `editor`, since the March 2025 spam wave (ACC-30).** The role and the rule are in the code (`DEFAULT_ROLE` and `grant_role`); I moved the reason and the ticket into a comment beside the check in accounts/users.py.

Nothing else needed a document, so the page is deleted. No code changed and no files were added.
