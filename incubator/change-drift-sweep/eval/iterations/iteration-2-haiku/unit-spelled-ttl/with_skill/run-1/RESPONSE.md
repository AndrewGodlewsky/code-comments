The idle session timeout is now 30 minutes. It was 15.

Changes:
- auth/settings.py: SESSION_TTL_S 900 -> 1800. The 60-second "Still there?" warning is unchanged, so the banner now appears at 29 minutes idle (1800 - 60 = 1740 s) and the session ends at 30.
- auth/sessions.py: module docstring "fifteen minutes" -> "thirty minutes".
- auth/views.py: sign_in docstring "fifteen minutes" -> "thirty minutes".
- auth/forms.py: docstring "a quarter of an hour" -> "half an hour".
- docs/console.md: banner timing "14 minutes" -> "29 minutes" (the figure derived from the new timeout and warning).
- docs/security.md: "Idle sessions end after 15 min" -> "30 min".

Left unchanged on purpose:
- docs/security.md: access tokens last 15 minutes. That is set by the company identity provider, not this service.
- docs/security.md and auth/reset.py: password-reset links expire after 15 minutes. This is a separate setting (RESET_LINK_TTL_S).
- auth/lockout.py and docs/security.md: the account lockout after 15 failed sign-ins. Unrelated.

Checks: python -m unittest passes (6 tests). The tests read SESSION_TTL_S, so they cover the new value without edits. A re-run of the drift sweep shows no remaining prose stating the old 15-minute idle timeout or the 14-minute banner time.
