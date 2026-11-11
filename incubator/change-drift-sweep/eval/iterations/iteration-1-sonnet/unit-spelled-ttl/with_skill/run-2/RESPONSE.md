The idle session timeout is now 30 minutes: `SESSION_TTL_S` in `auth/settings.py` went from 900 to 1800. I didn't run the tests.

I swept the comments, docstrings and docs for the old value (900 s, 15 min, "fifteen minutes", "a quarter of an hour") and for the figure derived from it. The "Still there?" banner appears `IDLE_WARNING_S` (60 s) before expiry, so it moves from 14 to 29 minutes (1800 - 60 = 1740 s).

Corrected, by file:
- `auth/settings.py`: the value, 900 to 1800. The comment names no number, so it stays.
- `auth/sessions.py`: module docstring, "fifteen minutes" to "thirty minutes".
- `auth/views.py`: `start` docstring, "fifteen minutes" to "thirty minutes".
- `auth/forms.py`: module docstring, "a quarter of an hour" to "half an hour".
- `docs/security.md`: "Idle sessions end after 15 min" to "30 min".
- `docs/console.md`: banner after "14 minutes" to "29 minutes".

Kept, because they are unrelated to the session timeout although they share the number 15 or 900:
- `RESET_LINK_TTL_S = 900` and the "fifteen minutes" docstring in `auth/reset.py`: the password-reset link lifetime, a separate setting.
- `docs/security.md`: "Password-reset links expire after 15 minutes", and "An account is locked after 15 failed sign-ins" (`MAX_FAILED_LOGINS`).
- `docs/security.md`: "Access tokens from the company identity provider last 15 minutes". This is an outside fact set by the identity team. If the console depends on those tokens, admins may still be forced to re-authenticate at 15 minutes. I can't tell from this repo, so please check it.

No records, ADRs, changelog or instruction files mention the old value. I found no drift that predates this change.
