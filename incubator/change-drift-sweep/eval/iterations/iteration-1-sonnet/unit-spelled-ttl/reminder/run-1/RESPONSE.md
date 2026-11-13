Raised the idle session timeout from 15 to 30 minutes (`SESSION_TTL_S` 900 -> 1800 in `auth/settings.py`).

Updated statements that described the old value:
- `auth/sessions.py` module docstring and `auth/views.py` docstring: "fifteen minutes" -> "thirty minutes".
- `auth/forms.py` docstring: "a quarter of an hour" -> "half an hour".
- `docs/console.md`: the "Still there?" banner now appears after 29 minutes (1800 - 60 s warning), not 14.
- `docs/security.md`: idle sessions end after 30 min.

Left alone on purpose (not the session timeout, same 15 / 900 coincidentally):
- `RESET_LINK_TTL_S = 900`, `reset.py` docstring and the security.md reset-link line (15 minutes).
- Lockout after 15 failed sign-ins (`MAX_FAILED_LOGINS`, `lockout.py`, security.md).
- Identity-provider access tokens lasting 15 minutes (outside fact, set by the identity team).

No mismatches found that my change did not cause. Tests reference `SESSION_TTL_S` symbolically; I did not run them.
