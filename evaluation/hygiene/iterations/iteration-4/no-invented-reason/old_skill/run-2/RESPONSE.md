The session idle timeout is now 15 minutes, down from 30.

Changed:
- `auth/settings.py`: `IDLE_TIMEOUT_MINUTES = 15`. This is the only value the code reads.
- `auth/sessions.py`: the module docstring said sessions expire after 30 minutes, so it now says 15.
- `docs/security.md`: the note that idle sessions are signed out after 30 minutes now says 15.

I did not find any other references to the timeout.

One thing I need from you: I didn't get a reason for the change. The code and docs now state the new value only, with no rationale. If there is a reason, such as a security policy or a compliance requirement, tell me and I will record it beside the setting in `auth/settings.py`.
