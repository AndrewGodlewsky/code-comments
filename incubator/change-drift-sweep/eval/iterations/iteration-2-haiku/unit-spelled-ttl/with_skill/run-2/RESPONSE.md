The idle session timeout is now 30 minutes, up from 15. Admins should no longer be signed out during long edits that have a gap of up to 30 minutes between requests.

What changed:

- `auth/settings.py`: `SESSION_TTL_S` goes from 900 to 1800.
- `auth/sessions.py` and `auth/views.py`: docstrings now say thirty minutes instead of fifteen.
- `auth/forms.py`: the docstring now says a form left idle for half an hour can no longer be saved, instead of a quarter of an hour.
- `docs/console.md`: the "Still there?" banner appears after 29 minutes idle, not 14. This is the 30-minute timeout minus the unchanged 60-second warning window (1800 - 60 = 1740 s = 29 min).
- `docs/security.md`: idle sessions end after 30 min, not 15.

Left unchanged on purpose:

- `RESET_LINK_TTL_S` and the password-reset link lifetime (15 minutes, `auth/reset.py` and `docs/security.md`): a separate setting, unrelated to the session timeout.
- The 15-failed-sign-in account lockout (`auth/lockout.py`, `docs/security.md`): unrelated to the session timeout.
- Access token lifetime of 15 minutes (`docs/security.md`): set by the company identity provider, an outside fact. Note that the service's 30-minute idle session can outlast a 15-minute access token, so a session may need a fresh token mid-session. Whether that is a problem depends on how the identity provider refresh works, which this change does not touch. Worth checking if admins still report sign-outs.

Tests: `python -m unittest` passes (6 tests). The session tests read the timeout from settings, so they needed no changes.
