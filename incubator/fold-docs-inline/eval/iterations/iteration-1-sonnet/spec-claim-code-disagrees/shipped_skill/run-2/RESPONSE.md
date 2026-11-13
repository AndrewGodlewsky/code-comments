I retired `docs/accounts.md` and deleted it. `docs/support.md` is untouched and nothing else linked to the deleted page.

One claim on the page was false, so I did not carry it into a comment. The page said usernames are case-insensitive (ACC-12). The code does not do that: `normalise_name` only strips surrounding whitespace, so `find_user("Ann")` and `find_user("ann")` find different accounts, and `register()` treats them as different names. No test covers case either way. I changed no code, since you asked for a doc move. Please decide whether ACC-12 is still the intended behaviour. If it is, the code needs a fix (e.g. lower-casing in `normalise_name`) and a test. If not, the requirement needs updating.

What moved:
- The admin-only editor rule and its reason (the March 2025 spam wave, ACC-30) is now a comment in `grant_role` in `accounts/users.py`.

What I did not add, because the code, names or tests already say it:
- Whitespace being ignored (`normalise_name` strips it; the test registers `" kim "`).
- `register()` raising `NameTaken` (the exception docstring and a test cover it).
- New accounts getting the `member` role (`DEFAULT_ROLE` and a test cover it).
