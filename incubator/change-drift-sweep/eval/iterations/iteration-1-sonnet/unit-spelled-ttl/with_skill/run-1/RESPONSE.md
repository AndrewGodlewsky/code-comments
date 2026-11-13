The idle session timeout is now 30 minutes: `SESSION_TTL_S` in `auth/settings.py` went from 900 to 1800. The tests pass.

I also swept the prose for the old value and corrected every description that still stated it, whether as digits, words, another unit or a derived figure:

- `auth/sessions.py`: module docstring "fifteen minutes" is now "thirty minutes".
- `auth/views.py`: docstring "fifteen minutes" is now "thirty minutes".
- `auth/forms.py`: docstring "a quarter of an hour" is now "half an hour".
- `docs/security.md`: "Idle sessions end after 15 min" is now "30 min".
- `docs/console.md`: the "Still there?" banner appears 14 minutes in because the warning comes 60 s before the end ((900-60)/60). With the new timeout it is (1800-60)/60 = 29, so it now says "After 29 minutes". The "a minute later" sign-out is unchanged.

Kept as written, because they share the number 15 but are about something else:
- The access-token lifetime in `docs/security.md` ("15 minutes"). It is set by the identity team, not this service, so it is an outside fact. A session can now outlive its identity-provider access token, so check that nothing depends on the two matching.
- The password-reset link lifetime: `RESET_LINK_TTL_S = 900`, the `auth/reset.py` docstring and `docs/security.md`. This is a separate setting.
- The lockout count of 15 failed sign-ins, in `auth/lockout.py`, `auth/settings.py` and `docs/security.md`.

The warning banner timing (`IDLE_WARNING_S`, 60 s) is unchanged. I found no instruction files, changelog, ADRs or other records that state the old value, and no drift that predates this change.
