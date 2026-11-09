The session idle timeout is now 15 minutes, down from 30.

Changes:
- `auth/settings.py`: `IDLE_TIMEOUT_MINUTES` changed from 30 to 15. `auth/sessions.py` reads this constant, so expiry behaviour follows it.
- `auth/sessions.py`: the module docstring said sessions expire after 30 minutes; it now says 15.
- `docs/security.md`: "Idle sessions are signed out after 30 minutes" now says 15 minutes.

I checked the repository for other mentions of the 30-minute value and found none. The constant's comment does not state a number, so it stays as is. I did not run any tests, since none were part of this repository.
