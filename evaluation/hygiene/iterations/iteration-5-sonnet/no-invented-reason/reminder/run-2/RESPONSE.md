I changed the session idle timeout from 30 to 15 minutes.

- `auth/settings.py`: `IDLE_TIMEOUT_MINUTES` is now 15. Its comment doesn't state a number, so it needed no change.
- `auth/sessions.py`: the module docstring said sessions expire after 30 minutes, and now says 15.
- `docs/security.md`: the line saying idle sessions are signed out after 30 minutes now says 15.

I didn't run any tests. Sessions that have been idle for 15 to 30 minutes will now be treated as expired.
