Idle sessions now end after 30 minutes instead of 15, so admins should no longer be signed out in the middle of long edits.

The change is `SESSION_TTL_S` in `auth/settings.py`, now 1800 seconds (was 900). The "Still there?" banner still appears 60 seconds before the session ends, so it now shows after 29 minutes of inactivity (1800 - 60 = 1740 seconds), and the admin is signed out a minute later if they do nothing.

I also updated the prose that stated the old value:
- `auth/sessions.py` and `auth/views.py` docstrings: "fifteen minutes" changed to "thirty minutes".
- `auth/forms.py` docstring: "a quarter of an hour" changed to "half an hour".
- `docs/console.md`: the banner time changed from 14 minutes to 29 minutes.
- `docs/security.md`: the idle session lifetime changed from 15 min to 30 min.

Left unchanged on purpose, because they describe other things:
- `auth/reset.py` and `docs/security.md` (password-reset links, 15 minutes): a separate setting, `RESET_LINK_TTL_S`.
- `auth/lockout.py` and `docs/security.md` (account lockout after 15 failed sign-ins): unrelated to the session timeout.
- `docs/security.md`, access token lifetime from the company identity provider (15 minutes): an outside fact that the identity team sets. Please check whether the console session depends on those tokens. If it does, admins could still be signed out at 15 minutes, and the identity team would need to change that lifetime too.

The existing unit tests pass (6 tests). They read the timeout from the settings constant, so they did not need changes.
