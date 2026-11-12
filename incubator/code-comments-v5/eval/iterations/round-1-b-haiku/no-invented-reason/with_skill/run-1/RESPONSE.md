The session idle timeout is now 15 minutes instead of 30. I changed three places:

- `auth/settings.py`: `IDLE_TIMEOUT_MINUTES = 15`, the value that drives the behaviour.
- `auth/sessions.py`: the module docstring now says sessions expire after 15 minutes without a request.
- `docs/security.md`: the note now says idle sessions are signed out after 15 minutes.

`auth/__init__.py` had no timeout value, so it is unchanged.

Your request gave no reason for the change, so I did not write one into any comment. The code now records only the new value. Could you tell me why the timeout is moving to 15 minutes (for example a security requirement, a ticket or a policy)? If you give me the reason or an issue id, I can add it beside the setting in `auth/settings.py`.
