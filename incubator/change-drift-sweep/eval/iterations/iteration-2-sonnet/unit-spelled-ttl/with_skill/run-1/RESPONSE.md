The idle session timeout is now 30 minutes: `SESSION_TTL_S` in `auth/settings.py` went from 900 to 1800 seconds. I searched all the code, comments and docs for the old value in digits, words and other units, and for figures derived from it.

I did not run the tests or the sweep script.

**Corrected, by file**
- `auth/settings.py`: `SESSION_TTL_S = 1800`.
- `auth/sessions.py`: the module docstring now says "thirty minutes" instead of "fifteen minutes".
- `auth/views.py`: the `sign_in` docstring now says "thirty minutes" instead of "fifteen minutes".
- `auth/forms.py`: the module docstring said "a quarter of an hour" and now says "half an hour".
- `docs/security.md`: "Idle sessions end after 30 min" instead of 15 min.
- `docs/console.md`: the banner appears after 29 minutes instead of 14. This figure is derived. The banner shows `IDLE_WARNING_S` (60 s) before the end, so it appears at 1800 - 60 = 1740 s = 29 min. The "a minute later" sign-out text is still true.

**Kept, because they are about something else**
- `auth/reset.py` and `RESET_LINK_TTL_S` (900 s, "fifteen minutes"), and the matching line in `docs/security.md`: the password-reset link lifetime is a separate setting.
- `MAX_FAILED_LOGINS = 15`, the "15 failed sign-ins" comment in `auth/lockout.py`, and the lockout line in `docs/security.md`: a count of failed sign-ins, not a duration.
- `docs/security.md`, "Access tokens ... last 15 minutes": this is an outside fact, set by the identity team. It is unchanged. Admins' sessions now outlast their identity-provider tokens, so check that the tokens don't force a sign-in sooner than 30 minutes.
- `IDLE_WARNING_S = 60`: unchanged. I kept the 60-second warning window as it was.

No records, instruction files or ADRs mention the old value, and there was no drift that predated this change.
