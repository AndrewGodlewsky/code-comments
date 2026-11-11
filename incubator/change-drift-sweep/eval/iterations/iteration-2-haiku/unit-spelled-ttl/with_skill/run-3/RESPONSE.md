The idle session timeout is now 30 minutes. Admins are signed out after 30 minutes without a request, up from 15, and every request still restarts the timer.

What changed:

- `auth/settings.py`: `SESSION_TTL_S` is now `1800` (was `900`). The "Still there?" banner still appears 60 seconds before sign-out (`IDLE_WARNING_S = 60`), so it now shows after 29 minutes idle instead of 14.
- `auth/sessions.py`, `auth/views.py`: docstrings now say "thirty minutes" instead of "fifteen minutes".
- `auth/forms.py`: the docstring now says "half an hour" instead of "a quarter of an hour", since a form left idle for half an hour can no longer be saved.
- `docs/console.md`: the banner timing now reads "After 29 minutes" (was 14), since 1800 s minus 60 s is 1740 s.
- `docs/security.md`: "Idle sessions end after 30 min" (was 15).

Kept as written:

- `auth/reset.py` and the "Password-reset links expire after 15 minutes" line in `docs/security.md`: these describe `RESET_LINK_TTL_S`, which is unchanged.
- `auth/lockout.py` and the lockout line in `docs/security.md`: "15 failed sign-ins" is `MAX_FAILED_LOGINS`, unrelated to the session timeout.
- `docs/security.md`, "Access tokens from the company identity provider last 15 minutes": an outside fact set by the identity team. Note that sessions can now run 30 minutes while those access tokens last 15. If the console depends on that token for requests, admins could still be signed out earlier than 30 minutes. Worth confirming with the identity team.

Drift the change did not cause: none.

Verification: `python -m unittest` runs 6 tests, all passing. The existing session tests use `settings.SESSION_TTL_S`, so they follow the new value. I did not add a test for the new 30-minute figure itself. The drift scan lists only the kept hits above.
