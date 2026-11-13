Idle session timeout is now 30 minutes (`SESSION_TTL_S = 1800` in `auth/settings.py`). The "Still there?" banner is derived from it, so it now appears after 29 minutes. I did not run the tests.

I also corrected every statement of the old 15-minute timeout: the docstrings in `auth/sessions.py`, `auth/views.py` and `auth/forms.py` (now "half an hour"), `docs/console.md` (29 minutes) and `docs/security.md` (30 min). I left the 15-minute password-reset link lifetime and the 15-failed-sign-in lockout alone, since they are separate settings.

Conflict to check: `docs/security.md` says access tokens from the company identity provider last 15 minutes, and that the identity team sets that lifetime. I left that line as written. If a session's validity depends on that token, admins will still be cut off at 15 minutes and this change will not fix the problem. I could not tell from the code whether it does, so please confirm with the identity team.

No reason for choosing 30 minutes was given, so I recorded only the new value and added no rationale. If there is one, such as the typical length of an edit, tell me and I will add it next to `SESSION_TTL_S`.
