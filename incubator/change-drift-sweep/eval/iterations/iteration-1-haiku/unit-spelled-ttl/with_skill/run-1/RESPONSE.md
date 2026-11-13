The idle session timeout is now 30 minutes, up from 15. Admins should no longer be signed out in the middle of long edits.

The change is `SESSION_TTL_S = 1800` in `auth/settings.py`. The "Still there?" banner still shows 60 seconds before the session ends, so it now appears at 29 minutes idle instead of 14. I updated the prose that described the old timeout:

- `auth/sessions.py` and `auth/views.py` docstrings: "fifteen minutes" is now "thirty minutes".
- `auth/forms.py` docstring: "a quarter of an hour" is now "half an hour", since a form left idle now expires after half an hour.
- `docs/console.md`: "After 14 minutes" is now "After 29 minutes" (1800 - 60 = 1740 s = 29 min).
- `docs/security.md`: "Idle sessions end after 15 min" is now "after 30 min".

Left unchanged on purpose:

- Password-reset links still expire after 15 minutes (`RESET_LINK_TTL_S`, `auth/reset.py`, and `docs/security.md`). This is a separate setting and was not part of the request.
- Access tokens from the company identity provider last 15 minutes (`docs/security.md`). That lifetime is set by the identity team, not this service.
- Account lockout after 15 failed sign-ins (`MAX_FAILED_LOGINS`, `auth/lockout.py`, `docs/security.md`). Unrelated to the session timeout.

The existing unit tests pass (`python -m unittest`, 6 tests). They read the constant rather than a hard-coded value, so they needed no change.

Note: a session that is not used for 30 minutes now ends. Raising the limit also lengthens how long a signed-in admin stays exposed if a device is left unattended, so the identity and security owners may want to confirm this trade-off.
