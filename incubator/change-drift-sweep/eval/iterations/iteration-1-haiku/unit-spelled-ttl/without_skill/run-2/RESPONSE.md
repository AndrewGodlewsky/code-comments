The idle session timeout for the admin console is now 30 minutes, up from 15. Admins will stay signed in through longer edits as long as they make a request at least every 30 minutes.

What changed:
- `auth/settings.py`: `SESSION_TTL_S` is now 1800 (was 900).
- The "Still there?" banner now appears at 29 minutes of inactivity, one minute before sign-out. That keeps the existing one-minute warning window.
- Docs and docstrings updated to match: `docs/security.md`, `docs/console.md`, `auth/sessions.py`, `auth/views.py`.

The unit tests pass (`python -m unittest`, 6 tests).

One thing to check: `docs/security.md` says access tokens from the company identity provider last 15 minutes. The identity team sets that lifetime, not this service. If those tokens are what expires mid-edit, admins could still be signed out before the new 30-minute idle timeout applies. This change does not touch that lifetime, so it is worth confirming with the identity team if the sign-outs continue.
