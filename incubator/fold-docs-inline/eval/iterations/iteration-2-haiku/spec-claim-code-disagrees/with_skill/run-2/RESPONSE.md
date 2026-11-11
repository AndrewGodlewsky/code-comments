# Fate list for docs/accounts.md

Page deleted: no kept claim remained, and you asked to retire it. Its text survives only in this file (see the not-migrated line below).

## Fates, in page order

1. "Usernames are case-insensitive (ACC-12): `find_user("Ann")` and `find_user("ann")` find the same account, and `register()` treats them as the same name."
   - Fate: **not migrated**. The code contradicts it.
   - Evidence: `accounts/names.py` `normalise_name` only calls `.strip()`, with no case folding. `accounts/users.py` `register` keys accounts by that stripped name (lines 17-20), so "Ann" and "ann" become separate accounts. `find_user` (line 25) is an exact dict lookup. No test covers case.
   - Question for you: which side is right? If case-insensitivity is the intent, the code needs changing (outside this task). If not, the claim should be dropped. ACC-12 is not referenced in the code.

2. "Spaces before or after a name are ignored."
   - Fate: **dropped**. The code already states it.
   - Evidence: `accounts/names.py` `normalise_name` (lines 4-5, `.strip()`); `tests/test_users.py` `test_register_and_find` (line 9, registers `" kim "`).

3. "`register()` raises `NameTaken` when the name is already in use."
   - Fate: **dropped**. The code already states it.
   - Evidence: `accounts/users.py` `register` (lines 18-19); `tests/test_users.py` `test_a_name_can_only_be_taken_once`.

4. "New accounts get the `member` role."
   - Fate: **dropped**. The code already states it.
   - Evidence: `accounts/users.py` `DEFAULT_ROLE = "member"` (line 5) and its use in `register` (line 20); `tests/test_users.py` line 10.

5. "Only an admin can grant `editor`" and "editor rights were limited to admins" (the same rule, two parts).
   - Fate: **dropped**. The code already states it.
   - Evidence: `accounts/users.py` `grant_role` (lines 29-30); `tests/test_users.py` `test_only_admins_grant_editor`.

6. "after the spam wave in March 2025 (ACC-30)."
   - Fate: **moved**. It is the reason for a constraint that the code cannot show.
   - Destination: `accounts/users.py`, `Directory.grant_role`, a comment above the editor check (line 30): `# Editor rights were limited to admins after the March 2025 spam wave (ACC-30).`

## Other files

- Other files that state a moved fact: none in this repository. `README.md` and `docs/support.md` do not state it.
- Files linking to `docs/accounts.md` or to a removed section: none. A grep for `accounts.md` found nothing.
- Gaps: the not-migrated claim (line 1) needs your decision. The page is gone, so restore that text from this file if you want to keep it as a spec.
