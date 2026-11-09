The session idle timeout is now 15 minutes, down from 30. I changed three places:

- `auth/settings.py`: `IDLE_TIMEOUT_MINUTES = 15`, the value the code reads.
- `auth/sessions.py`: the module docstring now says sessions expire after 15 minutes without a request.
- `docs/security.md`: now says idle sessions are signed out after 15 minutes.

I did not add a comment giving a reason for the change, because you did not give one. Could you tell me why the timeout is being shortened (for example a security policy, a compliance requirement or a product decision)? If you give me the reason, I will record it beside the constant with its source.

No commits were made.
