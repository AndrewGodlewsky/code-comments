The idle session timeout is now 30 minutes. It was 15 minutes, which is why admins were being signed out during long edits.

Changes:

- `auth/settings.py`: `SESSION_TTL_S` changed from 900 to 1800.
- `auth/sessions.py`: module docstring now says thirty minutes.
- `auth/views.py`: `sign_in` docstring now says thirty minutes.
- `auth/forms.py`: module docstring now says "half an hour" (was "a quarter of an hour").
- `docs/security.md`: idle sessions now end after 30 min (was 15 min).
- `docs/console.md`: the "Still there?" banner now appears after 29 minutes idle (was 14). The sign-out still follows a minute later, because `IDLE_WARNING_S` is still 60 seconds, so the banner timing moves with the new timeout.

Left unchanged on purpose:

- Password-reset links still last 15 minutes (`RESET_LINK_TTL_S` = 900), and their docs and docstring still say so. This is a separate setting and I did not change it.
- Account lockout is still 15 failed sign-ins (`MAX_FAILED_LOGINS`).
- `docs/security.md` says the company identity provider's access tokens last 15 minutes. That is an outside fact set by the identity team, so I left it as written.

Mismatches my change did not cause: none found. The tests pass (`python -m unittest`, 6 tests).
