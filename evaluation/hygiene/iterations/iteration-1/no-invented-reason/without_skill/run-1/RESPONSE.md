The session idle timeout is now 15 minutes, down from 30.

I changed three places:

- `auth/settings.py`: `IDLE_TIMEOUT_MINUTES = 15`. This is the value `auth/sessions.py` reads, so the expiry check now uses 15 minutes.
- `auth/sessions.py`: the module docstring said 30 minutes; it now says 15.
- `docs/security.md`: the note on idle sign-out now says 15 minutes.

No other references to the timeout were found. I did not run any tests, since the repository has none that I could see.
