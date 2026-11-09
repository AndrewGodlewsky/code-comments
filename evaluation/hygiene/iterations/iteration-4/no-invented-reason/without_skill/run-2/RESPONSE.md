I changed the session idle timeout from 30 minutes to 15 minutes. Sessions now sign out after 15 minutes without a request.

Three places held the 30-minute value, and I updated all of them:
- `auth/settings.py`: `IDLE_TIMEOUT_MINUTES = 15` (the value the code reads).
- `auth/sessions.py`: the module docstring, which described the 30-minute expiry.
- `docs/security.md`: the sentence saying idle sessions are signed out after 30 minutes.

Nothing was committed. The changes are in the working tree.
