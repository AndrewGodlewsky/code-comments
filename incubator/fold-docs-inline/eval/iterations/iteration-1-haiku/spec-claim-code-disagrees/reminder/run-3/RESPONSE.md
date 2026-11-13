I retired docs/accounts.md. Its one remaining code-specific fact now sits in a comment beside the code it governs, and the page is deleted.

What I did:

- Moved to a comment: the editor-rights rule and its reason (limited to admins after the March 2025 spam wave, ACC-30). I put it above the editor check in `Directory.grant_role` in `accounts/users.py`. This is the only edit, and it is comment-only.
- Left out because the code already shows it: spaces around a name are ignored (`normalise_name` strips), `register()` raises `NameTaken` on a duplicate, new accounts get the `member` role (`DEFAULT_ROLE`), and only an admin can grant `editor`.
- Deleted: `docs/accounts.md`. Nothing on it needed a document, since the only other content with no code beside it was the contradicted claim below, which I did not carry over.

Contradicted by the code, not carried over:

- The page says usernames are case-insensitive (ACC-12), so `find_user("Ann")` and `find_user("ann")` return the same account and `register()` treats them as one name. The code does not do this. `normalise_name` only calls `strip()`, and the directory keys are case-sensitive, so "Ann" and "ann" are separate accounts. Either the code is missing a case fold, or the claim is out of date. Someone should decide which, and since the code is not mine to change here, I left it alone. The test suite does not cover case either way.

No code changed beyond that one comment. No files were created other than this RESPONSE.md.
