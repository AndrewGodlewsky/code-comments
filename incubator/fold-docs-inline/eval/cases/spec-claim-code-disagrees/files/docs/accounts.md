# Accounts

- Usernames are case-insensitive (ACC-12): `find_user("Ann")` and `find_user("ann")` find
  the same account, and `register()` treats them as the same name.
- Spaces before or after a name are ignored.
- `register()` raises `NameTaken` when the name is already in use.
- New accounts get the `member` role. Only an admin can grant `editor`: editor rights were
  limited to admins after the spam wave in March 2025 (ACC-30).
