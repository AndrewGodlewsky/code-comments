The idle session timeout is now 30 minutes, up from 15. I didn't run the tests.

The change is `SESSION_TTL_S` in `auth/settings.py`, which is now 1800 seconds. The "Still there?" banner still appears 60 seconds before the session ends, so it now shows after 29 minutes of inactivity instead of 14.

I also updated the text that quoted the old value:
- the docstrings in `auth/sessions.py`, `auth/views.py` and `auth/forms.py`
- the idle-session line in `docs/security.md`
- the banner timing in `docs/console.md` (14 minutes became 29)

I left these at 15 because they are separate settings, not the idle timeout:
- password-reset link lifetime (`RESET_LINK_TTL_S`)
- the failed-sign-in lockout threshold
- identity-provider access tokens, which the identity team controls

The existing tests read the timeout from settings, so they follow the new value.

A longer idle window means an unattended admin session stays open twice as long.
