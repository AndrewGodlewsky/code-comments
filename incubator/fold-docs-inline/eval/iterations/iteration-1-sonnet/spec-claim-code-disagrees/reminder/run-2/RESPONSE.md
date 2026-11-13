I retired `docs/accounts.md` and deleted it. Nothing on it still needed a document, and `docs/support.md` is untouched. I changed no code, only added one comment, and created no new files besides this message.

**Moved into a comment**
- The reason editor rights are admin-only (the March 2025 spam wave, ACC-30) is now a one-line comment in `accounts/users.py`, directly above the `role == "editor"` check in `grant_role`. The check itself is visible in the code, but the reason isn't.

**Left out because the code already shows it**
- "Spaces before or after a name are ignored": `normalise_name` in `accounts/names.py` strips them.
- "`register()` raises `NameTaken`": visible in `register()`, and covered by a test.
- "New accounts get the `member` role": `DEFAULT_ROLE = "member"`.
- "Only an admin can grant `editor`": the check in `grant_role`, also tested. Only the reason was kept.

**Contradicted by the code, not carried over**
- The page says usernames are case-insensitive (ACC-12), so `find_user("Ann")` and `find_user("ann")` find the same account. The code doesn't do that. `normalise_name` only calls `strip()`, so "Ann" and "ann" are different accounts, and `register()` accepts both. No test covers case. Either the code is missing the lowercasing that ACC-12 asked for, or the requirement changed. You'll want to check ACC-12 and decide. I didn't touch the code, and I didn't write the claim into a comment.
