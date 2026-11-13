The idle session timeout is now 30 minutes. In `auth/settings.py`, `SESSION_TTL_S` changed from 900 to 1800. The "Still there?" banner still appears 60 seconds before the session ends, so it now shows at 29 minutes idle, and the admin is signed out a minute after that if they do not respond.

I also corrected the comments and docs that stated the old 15-minute timeout:
- `auth/sessions.py` module docstring: "fifteen minutes" to "thirty minutes".
- `auth/views.py` `sign_in` docstring: "fifteen minutes" to "thirty minutes".
- `auth/forms.py` module docstring: "a quarter of an hour" to "half an hour".
- `docs/console.md`: the banner timing changed from "14 minutes" to "29 minutes".
- `docs/security.md`: idle sessions now end after "30 min".

The password-reset link lifetime (15 minutes) and the 15-failure lockout are unchanged.

Conflict to check: `docs/security.md` says access tokens from the company identity provider last 15 minutes, and the identity team sets that lifetime. If those tokens are what keeps an admin signed in, a 30-minute idle session may still end early at the 15-minute token expiry. I left that statement as written because it describes an outside system. Please confirm with the identity team whether the token lifetime limits the session.

Tests: `python -m unittest` ran 6 tests, all passing. I did not add tests, because the existing session tests read the timeout from settings.
