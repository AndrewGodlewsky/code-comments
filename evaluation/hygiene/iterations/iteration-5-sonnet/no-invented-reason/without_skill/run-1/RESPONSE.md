I changed the session idle timeout from 30 minutes to 15.

- `auth/settings.py`: `IDLE_TIMEOUT_MINUTES` is now 15. This is the value the code actually uses.
- `auth/sessions.py`: updated the module docstring, which said 30 minutes.
- `docs/security.md`: updated the sentence saying idle sessions are signed out after 30 minutes.

I haven't run anything, since the repository has no tests. Users idle for 15 minutes or more will now be signed out.
