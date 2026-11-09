The session idle timeout is now 15 minutes, down from 30.

Changed:
- auth/settings.py: `IDLE_TIMEOUT_MINUTES = 15` (the value that drives the expiry check in auth/sessions.py).
- auth/sessions.py: the module docstring now says sessions expire after 15 minutes.
- docs/security.md: now says idle sessions are signed out after 15 minutes.

No code logic changed. The expiry check reads the constant, so it picks up the new value.

One thing I need from you: you didn't say why the timeout is changing. I left the code comments to state only the new value. If there is a reason (for example a security requirement, a ticket, or a policy), please send it and I will add it beside the setting.
