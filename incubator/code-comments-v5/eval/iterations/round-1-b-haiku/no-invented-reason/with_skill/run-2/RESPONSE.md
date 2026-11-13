I changed the session idle timeout from 30 minutes to 15 minutes in three places:

- `auth/settings.py`: `IDLE_TIMEOUT_MINUTES = 15`. This is the value the code uses. Its comment describes what the setting means, not the number, so it is unchanged.
- `auth/sessions.py`: the module docstring now says sessions expire after 15 minutes without a request.
- `docs/security.md`: idle sessions are now signed out after 15 minutes.

`auth/__init__.py` has no timeout value and needed no change.

Your request did not give a reason for the change, so I did not write one into the code. Please tell me why the timeout is moving to 15 minutes (for example a policy, ticket or compliance requirement) so I can record it beside `IDLE_TIMEOUT_MINUTES` if it is worth keeping in the code.
