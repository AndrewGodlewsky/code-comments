Raised the idle session timeout from 15 to 30 minutes (`SESSION_TTL_S` 900 -> 1800 in `auth/settings.py`).

Updated text that stated the old value:
- `auth/sessions.py` docstring and `auth/views.py` docstring: "fifteen minutes" -> "thirty minutes".
- `auth/forms.py` docstring: "a quarter of an hour" -> "half an hour".
- `docs/security.md`: idle sessions end after 30 min.
- `docs/console.md`: the "Still there?" banner now appears after 29 minutes (30 minus the 60 s `IDLE_WARNING_S`, previously 14).

Left unchanged because they are separate values that happen to be 15 or 900 (not caused by this change):
- `RESET_LINK_TTL_S = 900`, the "fifteen minutes" in `auth/reset.py` and "15 minutes" for reset links in `docs/security.md`.
- The lockout limit of 15 failed sign-ins (`auth/lockout.py`, `auth/settings.py`, `docs/security.md`).
- The identity provider's 15-minute access tokens in `docs/security.md`, an outside fact set by another team.

Tests use the setting by name, so nothing there needed editing; I did not run them.
