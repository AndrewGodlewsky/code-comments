I changed the session idle timeout from 30 minutes to 15.

Changes:
- `auth/settings.py`: `IDLE_TIMEOUT_MINUTES` is now `15`.
- `auth/sessions.py`: the module docstring said "30 minutes", which is now false. It now points to `IDLE_TIMEOUT_MINUTES` in `auth/settings.py` rather than repeating the value.
- `docs/security.md`: "Idle sessions are signed out after 30 minutes" now reads 15 minutes.

I did not find a reason for the change in the request, the code, or the docs, so I did not add one to any comment. Could you tell me why the timeout is moving to 15 minutes (for example, a security requirement or a ticket)? If there is a ticket, I can add its id to the setting's comment.

I did not run any tests, since none were in the repository.
