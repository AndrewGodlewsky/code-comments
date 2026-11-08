The session idle timeout is now 15 minutes, down from 30.

Changed:
- auth/settings.py: `IDLE_TIMEOUT_MINUTES = 15`. The code reads this constant, so it sets the actual behaviour.
- auth/sessions.py: the module docstring now says sessions expire after 15 minutes without a request.
- docs/security.md: now says idle sessions are signed out after 15 minutes.

I did not add a comment explaining the change because you did not give a reason for it. If you tell me why the timeout is being shortened (for example a security policy or a compliance requirement), I can record that reason beside the constant.
