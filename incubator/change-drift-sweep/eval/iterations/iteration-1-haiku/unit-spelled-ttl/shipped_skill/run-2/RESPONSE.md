I raised the idle session timeout from 15 to 30 minutes. The change is in `auth/settings.py` (`SESSION_TTL_S = 1800`).

The "Still there?" banner still appears 60 seconds before the session ends, so it now shows at 29 minutes and the admin is signed out at 30. I updated the comments and docs that described the old timing: `auth/sessions.py`, `auth/views.py`, `auth/forms.py`, `docs/security.md` and `docs/console.md`. The password-reset link lifetime (15 minutes) and the lockout threshold are unchanged.

The tests pass (`python -m unittest`, 6 tests).

Please check one thing: `docs/security.md` says access tokens from the company identity provider last 15 minutes, and the identity team sets that lifetime. Idle sessions now last 30 minutes, so if the console depends on those tokens, admins could still be signed out at 15 minutes. I did not change that statement because it is not ours to change. Could you confirm with the identity team whether the console uses those tokens for sessions?

I did not find a reason in the repository for the 30-minute value. I assumed it comes from the request to stop sign-outs during long edits. If there is a specific policy or ticket behind it, please send it so I can reference it in `auth/settings.py`.
