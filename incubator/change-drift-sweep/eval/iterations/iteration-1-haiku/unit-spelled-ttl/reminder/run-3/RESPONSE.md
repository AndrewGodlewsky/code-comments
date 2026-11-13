The idle session timeout is now 30 minutes. `SESSION_TTL_S` in `auth/settings.py` changed from 900 to 1800. The "Still there?" banner still appears 60 seconds before the session ends (`IDLE_WARNING_S` is unchanged), so it now appears at 29 minutes idle.

I updated the text that described the old 15-minute and 14-minute figures:
- `auth/sessions.py` module docstring: "fifteen minutes" to "thirty minutes".
- `auth/views.py` `sign_in` docstring: "fifteen minutes" to "thirty minutes".
- `auth/forms.py` module docstring: "a quarter of an hour" to "half an hour".
- `docs/security.md`: "Idle sessions end after 15 min" to "30 min".
- `docs/console.md`: the banner point, which was 14 minutes (900 − 60 seconds), is now 29 minutes (1800 − 60 seconds).

I left these unchanged because they are not about the session timeout:
- `auth/reset.py` docstring and `RESET_LINK_TTL_S = 900` in `auth/settings.py`: password-reset link lifetime.
- `docs/security.md`: "Password-reset links expire after 15 minutes."
- `docs/security.md`: "Access tokens from the company identity provider last 15 minutes." This is an outside fact set by the identity team.
- `MAX_FAILED_LOGINS` and the lockout comment, which concern failed sign-ins.

Mismatches my change did not cause: none found. The tests pass (`python -B -m unittest`, 6 tests, OK). The tests use the settings constants, so they needed no edits.
