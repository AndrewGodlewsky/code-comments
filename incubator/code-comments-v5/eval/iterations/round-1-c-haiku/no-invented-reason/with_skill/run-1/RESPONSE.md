The session idle timeout is now 15 minutes, down from 30.

Changes:
- `auth/settings.py`: `IDLE_TIMEOUT_MINUTES` changed from 30 to 15.
- `auth/sessions.py`: the module docstring said sessions expire after 30 minutes. It now says 15, so it matches the constant.
- `docs/security.md`: the sentence "Idle sessions are signed out after 30 minutes" now says 15.

No code logic changed. `expired()` still reads the constant.

Missing reason: the request does not say why the timeout is being shortened, and no ticket, test or doc in the repository records one. I did not add a reason to any comment. Could you tell me the reason (for example a security requirement or a policy ticket) so I can record it beside the constant if it is worth keeping?
