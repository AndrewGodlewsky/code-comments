# Retire docs/accounts.md: fate list

I deleted `docs/accounts.md`. No claim on it still needs a document, but one claim contradicts the code, so it was not moved and needs your decision. `docs/support.md` and the `docs/` folder are unchanged. The only code edit is one comment in `accounts/users.py`.

## Fate list (page order)

1. Lines 3-4: "Usernames are case-insensitive (ACC-12): `find_user("Ann")` and `find_user("ann")` find the same account, and `register()` treats them as the same name."
   - Fate: **not migrated**
   - Evidence: `accounts/names.py` `normalise_name` only strips whitespace. `accounts/users.py` `register` (line 17) and `find_user` (line 25) key the dict by that stripped name, so "Ann" and "ann" are separate accounts. The code is case-sensitive; the page says case-insensitive, citing ACC-12.

2. Line 4: "Spaces before or after a name are ignored."
   - Fate: **dropped**
   - Evidence: `accounts/names.py` line 5 (`name.strip()`), used by `register` and `find_user`; `tests/test_users.py` lines 9-10 (`" kim "`).

3. Line 6: "`register()` raises `NameTaken` when the name is already in use."
   - Fate: **dropped**
   - Evidence: `accounts/users.py` lines 18-19; `tests/test_users.py` lines 12-16.

4. Line 7: "New accounts get the `member` role."
   - Fate: **dropped**
   - Evidence: `accounts/users.py` line 5 (`DEFAULT_ROLE`) and line 20; `tests/test_users.py` line 10.

5. Line 7: "Only an admin can grant `editor`."
   - Fate: **dropped**
   - Evidence: `accounts/users.py` lines 29-30 in `grant_role`; `tests/test_users.py` lines 18-24.

6. Lines 7-8: "editor rights were limited to admins after the spam wave in March 2025 (ACC-30)."
   - Fate: **moved**
   - Destination: `accounts/users.py`, `Directory.grant_role`, as a comment at line 29 above the editor check on line 30. The reason is not in the code, and the ticket id is kept.

Headings: `# Accounts` is not a claim and is removed with the page.

## Other files to reconcile

- Moved fact: no other file states the March 2025 reason or ACC-30. The admin-only rule is also tested in `tests/test_users.py` lines 18-24, but the test does not state the reason.
- Links: nothing links to `docs/accounts.md`. `README.md` has no link to it.

## Gaps and decisions for you

- **Case-insensitive usernames (ACC-12):** please decide which side is right. The code is case-sensitive, and the page says the opposite. Because the page is deleted, the claim now survives only in this reply and in ticket ACC-12, which I could not check here. If the page is right, that is a code change, which this exercise does not make.
- **ACC-30 and the March 2025 spam wave:** I could not verify the history from this repository. The reason is moved as the page states it.
- **Deleted page:** `docs/accounts.md` is gone. Its only unmigrated content is the case-insensitivity claim quoted above.
