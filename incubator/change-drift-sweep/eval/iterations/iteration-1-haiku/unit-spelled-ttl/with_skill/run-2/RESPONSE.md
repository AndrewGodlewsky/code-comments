The idle session timeout is now 30 minutes. `SESSION_TTL_S` in `auth/settings.py` changed from 900 to 1800, so admins stay signed in for 30 minutes without a request instead of 15.

The "Still there?" banner still appears 60 seconds before the session ends, so it now shows after 29 minutes idle (1800 - 60 = 1740 s). I updated the docs and docstrings that stated the old values:

- `auth/sessions.py` and `auth/views.py`: docstrings now say "thirty minutes".
- `auth/forms.py`: docstring now says "half an hour".
- `docs/console.md`: the banner timing is now "After 29 minutes".
- `docs/security.md`: idle sessions now end "after 30 min".

Kept as written:
- `docs/security.md`: "Access tokens ... last 15 minutes". This is an outside fact set by the company identity team, not this service.
- `auth/reset.py` and `docs/security.md`: password-reset link lifetime (15 minutes). This is `RESET_LINK_TTL_S`, a separate setting that I did not change.
- `auth/lockout.py` and `docs/security.md`: the 15 failed sign-ins lockout. This is `MAX_FAILED_LOGINS`, unrelated to the session timeout.

No drift was found beyond what I changed. The existing tests pass (`python -m unittest`, 6 tests). Please confirm the 29-minute banner timing is what you want, since the warning window moves with the timeout.
