I retired `docs/accounts.md`. One claim moved into a comment, four were already stated by the code, and one contradicts the code, so I left it out and need your decision on it. Nothing on the page remained to keep, so I deleted it.

## Fate list

1. "Usernames are case-insensitive (ACC-12)" — **Not migrated.** `accounts/names.py:5` `normalise_name` only strips whitespace and never lowercases. `accounts/users.py:17-25` keys accounts on that raw string, so names are case-sensitive. Actual value: "Ann" and "ann" are different keys.
2. "`find_user("Ann")` and `find_user("ann")` find the same account" — **Not migrated.** Same evidence as claim 1: `find_user` (`users.py:25`) looks up the exact normalised string, so the two calls return different results (one can return `None`).
3. "`register()` treats them as the same name" — **Not migrated.** `users.py:17-19` checks `key in self._accounts` with no case folding, so `register("Ann")` and `register("ann")` both succeed.
4. "Spaces before or after a name are ignored" — **Dropped.** The code states it at `accounts/names.py:5` (`name.strip()`), used by `register` and `find_user`. `tests/test_users.py:9-10` covers `" kim "`.
5. "`register()` raises `NameTaken` when the name is already in use" — **Dropped.** `accounts/users.py:18-19` states it, and `tests/test_users.py:12-16` covers it.
6. "New accounts get the `member` role" — **Dropped.** `accounts/users.py:5` (`DEFAULT_ROLE`) and `:20` state it, and `tests/test_users.py:10` checks it.
7. "Only an admin can grant `editor`" — **Dropped.** `accounts/users.py:29-30` enforces it, and `tests/test_users.py:18-24` checks it.
8. "editor rights were limited to admins after the spam wave in March 2025 (ACC-30)" — **Moved** to the docstring of `Directory.grant_role` in `accounts/users.py`. The reason for the editor check lives only in this sentence, and a later editor who touches the check needs it. The ticket id is kept. This is a judgment call: if you treat it as decision history rather than the reason for the check, tell me and I will move it to a document instead.

## Changes

- `accounts/users.py`: added a docstring to `grant_role` with the ACC-30 reason. No code changed.
- `docs/accounts.md`: deleted. No kept claims remained. Claim 1 is quoted above so the case-insensitivity text is not lost.
- No other files were changed.

## Other files and links

- No other file states the moved fact. The grep for `accounts.md`, `ACC-30` and `docs/` found no other references in this repository.
- No file links to `docs/accounts.md`.
- `docs/support.md` is untouched and out of scope for this retirement.

## Gaps and your decision

- **Case-insensitivity (claims 1-3):** the docs and ticket ACC-12 say usernames are case-insensitive, but the code is case-sensitive. Which is right is your call. If the docs are right, the fix is a code change (lowercase in `normalise_name` or the lookup key), which this task does not make. If the code is right, ACC-12's intent is out of date and should be recorded somewhere, since the page is gone.
- **Where the ACC-30 reason belongs:** see the judgment call on claim 8 above.
