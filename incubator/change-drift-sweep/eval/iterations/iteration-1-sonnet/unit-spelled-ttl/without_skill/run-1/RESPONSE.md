Raised the idle session timeout from 15 to 30 minutes: `SESSION_TTL_S` in `auth/settings.py` is now 1800. Tests pass.

I also updated the text that described the old value: the docstrings in `auth/sessions.py`, `auth/views.py` and `auth/forms.py`, `docs/security.md`, and `docs/console.md`. The "Still there?" banner appears 60 seconds before sign-out, so it now shows after 29 minutes instead of 14.

I left the other 15s alone because they are separate settings: the identity provider's access-token lifetime (set by the identity team), the password-reset link lifetime, and the failed-sign-in lockout count.

Note that a longer timeout also means an unattended admin session stays open twice as long.
