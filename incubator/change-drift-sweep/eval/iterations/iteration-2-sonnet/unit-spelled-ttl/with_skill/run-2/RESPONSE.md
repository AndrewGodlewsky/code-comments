The idle session timeout is now 30 minutes. `SESSION_TTL_S` in `auth/settings.py` went from 900 to 1800, and the tests pass.

I also swept the comments and docs for prose that still gave the old 15 minutes. I corrected these:
- `auth/sessions.py`: module docstring now says "thirty minutes".
- `auth/views.py`: the `sign_in` docstring now says "thirty minutes".
- `auth/forms.py`: "a quarter of an hour" is now "half an hour".
- `docs/security.md`: "Idle sessions end after 30 min".
- `docs/console.md`: the "Still there?" banner appears after 29 minutes, not 14. The banner still shows 60 seconds before the end (`IDLE_WARNING_S`), so it is 1800 - 60 = 1740 s = 29 min.

I left these alone because they are about other settings that happen to share the number 15:
- Reset-link lifetime (`RESET_LINK_TTL_S = 900`, `auth/reset.py` docstring, `docs/security.md`).
- The lockout threshold of 15 failed sign-ins (`auth/lockout.py`, `auth/settings.py`, `docs/security.md`).
- The 15-minute access-token lifetime in `docs/security.md`. That is the identity team's setting and not ours. It is now shorter than our session, so a session can outlive its access token. Check that this is fine.

There were no records or instruction files to keep, and none of the prose was already wrong before this change.
