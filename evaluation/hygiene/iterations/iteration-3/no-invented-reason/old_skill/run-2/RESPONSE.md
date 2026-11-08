The session idle timeout is now 15 minutes, down from 30.

Changes (uncommitted):
- `auth/settings.py`: `IDLE_TIMEOUT_MINUTES = 15`. This is the value that drives expiry.
- `auth/sessions.py`: the module docstring said sessions expire after 30 minutes. I changed it to 15 so it stays true.
- `docs/security.md`: said idle sessions are signed out after 30 minutes. I changed it to 15.

Nothing else was touched. `expired()` reads the setting, so no logic change was needed.

One thing I need from you: I wasn't given a reason for the change. The code and docs now record only the new value. If there is a reason, such as a security requirement or a policy ticket, tell me and I will add it next to the setting in `auth/settings.py`.
