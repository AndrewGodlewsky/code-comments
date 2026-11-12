The session idle timeout is now 15 minutes instead of 30.

Changes:
- `auth/settings.py`: `IDLE_TIMEOUT_MINUTES` changed from 30 to 15. This is the only value that controls the timeout; `auth/sessions.py` reads it.
- `auth/sessions.py`: the module docstring said sessions expire after 30 minutes. It now says 15, so it matches the code.
- `docs/security.md`: the sentence about idle sessions being signed out after 30 minutes now says 15.

I did not add a comment explaining the change. Nothing you sent, and no test, caller or doc in the repo, gives a reason for moving the timeout to 15 minutes, so I did not invent one.

Missing reason: could you tell me why the timeout is being shortened (for example a security policy, a compliance requirement or a ticket)? If you give me the reason or a tracking issue id, I will add it beside `IDLE_TIMEOUT_MINUTES` in `auth/settings.py`.

Nothing else relies on the old value that I could find in these files. `auth/__init__.py` only has a module docstring and needed no change.
