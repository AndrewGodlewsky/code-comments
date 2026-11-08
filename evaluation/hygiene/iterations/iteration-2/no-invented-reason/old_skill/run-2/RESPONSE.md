The session idle timeout is now 15 minutes, down from 30.

Changed:
- `auth/settings.py`: `IDLE_TIMEOUT_MINUTES = 15` (the constant that `auth/sessions.py` reads).
- `auth/sessions.py`: the module docstring said sessions expire after 30 minutes; it now says 15, so it matches the code.
- `docs/security.md`: the sentence saying idle sessions are signed out after 30 minutes now says 15.

No other occurrences of the 30-minute value remained in the directory. The timeout logic in `expired()` is unchanged; it reads the constant.

Not verified: I did not run any tests or the app, since this directory has no test suite I could find. If anything outside this directory (deployment config, a client-side timer, or a separate copy of the value) also enforces 30 minutes, it would not be covered by this change.
