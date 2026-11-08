The session idle timeout is now 15 minutes instead of 30.

Changes:
- `auth/settings.py`: `IDLE_TIMEOUT_MINUTES` changed from 30 to 15. This is the value the expiry check uses.
- `auth/sessions.py`: the module docstring said sessions expire after 30 minutes; it now says 15.
- `docs/security.md`: the note saying idle sessions are signed out after 30 minutes now says 15.

No other references to the 30-minute timeout turned up in the repository. Nothing was committed.
