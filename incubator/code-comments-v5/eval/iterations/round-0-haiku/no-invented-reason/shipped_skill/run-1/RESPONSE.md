I changed the session idle timeout from 30 minutes to 15 minutes in three places:

- `auth/settings.py`: `IDLE_TIMEOUT_MINUTES = 15`
- `auth/sessions.py`: the module docstring now says sessions expire after 15 minutes without a request.
- `docs/security.md`: idle sessions are now described as signed out after 15 minutes.

I did not add a reason for the change to any comment, because you did not give one. Can you tell me why the timeout is being shortened (for example a security requirement, a ticket or a policy)? If you share it, I will record it beside the constant in `auth/settings.py`, with the issue id if there is one.

No code was committed.
