I changed the session idle timeout from 30 minutes to 15 minutes in three places:

- `auth/settings.py`: `IDLE_TIMEOUT_MINUTES = 15`
- `auth/sessions.py`: the module docstring now says sessions expire after 15 minutes without a request.
- `docs/security.md`: idle sessions are signed out after 15 minutes.

`auth/__init__.py` has no reference to the timeout, so I left it unchanged.

No reason for the change was given in the request, ticket or surrounding code, so I did not add one to any comment. Could you tell me why the timeout is moving to 15 minutes (for example a security requirement, a compliance rule or a product decision)? If there is a ticket or issue id, I can add it as a pointer in the code.
