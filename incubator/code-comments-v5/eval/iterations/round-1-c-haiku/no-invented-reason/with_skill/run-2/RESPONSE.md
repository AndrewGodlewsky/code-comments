I changed the session idle timeout from 30 minutes to 15 minutes in three places:

- `auth/settings.py`: `IDLE_TIMEOUT_MINUTES = 15`
- `auth/sessions.py`: the module docstring now says sessions expire after 15 minutes without a request.
- `docs/security.md`: idle sessions are signed out after 15 minutes.

Nothing else changed. `auth/__init__.py` had no timeout reference.

The request gave no reason for the change, and the files do not record one, so I did not write a rationale into any comment. If there is a reason (a security policy, a compliance requirement, a ticket), please send it and I will add it beside the constant in `auth/settings.py`.
