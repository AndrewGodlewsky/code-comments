I changed the session idle timeout from 30 minutes to 15.

- `auth/settings.py`: `IDLE_TIMEOUT_MINUTES` is now 15. This is the value the code actually uses.
- `auth/sessions.py`: updated the module docstring to say 15 minutes.
- `docs/security.md`: updated the sentence about idle sign-out to say 15 minutes.

I didn't run any tests. Sessions that have been idle for 15 to 30 minutes will now be treated as expired.
