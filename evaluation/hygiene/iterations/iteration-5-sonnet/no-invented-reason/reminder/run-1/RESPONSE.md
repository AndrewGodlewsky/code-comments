The session idle timeout is now 15 minutes instead of 30.

- `auth/settings.py`: `IDLE_TIMEOUT_MINUTES` changed from 30 to 15. This is the only value the code reads.
- `auth/sessions.py`: the module docstring said "30 minutes", so I updated it to 15.
- `docs/security.md`: the line saying idle sessions are signed out after 30 minutes now says 15.

The comment above the setting doesn't mention a number, so it's still accurate and I left it alone. I didn't add any comments. I haven't run anything, because the repository has no tests.
