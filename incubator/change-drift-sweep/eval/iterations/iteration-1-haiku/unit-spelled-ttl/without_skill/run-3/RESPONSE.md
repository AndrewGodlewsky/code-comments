Done. The idle session timeout is now 30 minutes, up from 15, so admins should stay signed in through longer edits.

What changed:
- `auth/settings.py`: `SESSION_TTL_S` is now `1800` (was `900`).
- The "Still there?" banner still appears one minute before sign-out, so it now shows after 29 minutes idle instead of 14.
- Updated the matching docs to say 30 minutes: `docs/security.md`, `docs/console.md` (29 minutes for the banner), and the docstrings in `auth/sessions.py` and `auth/views.py`.

I left the password-reset link lifetime (15 minutes) and the identity provider access token lifetime (15 minutes, set by the identity team) unchanged. Those are separate settings from the idle timeout.

Tests: `python -m unittest` passes (6 tests).
