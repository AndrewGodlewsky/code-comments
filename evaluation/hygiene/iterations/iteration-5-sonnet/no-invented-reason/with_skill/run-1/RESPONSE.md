I changed the session idle timeout from 30 minutes to 15.

- `auth/settings.py`: `IDLE_TIMEOUT_MINUTES` is now 15.
- `auth/sessions.py`: the module docstring now says 15 minutes.
- `docs/security.md`: now says idle sessions are signed out after 15 minutes.

Nothing in the repo or your request says why the timeout is changing, so I recorded only the new value and added no rationale comment. If there is a reason, such as a security requirement or a policy, tell me and I can record it next to the setting.
