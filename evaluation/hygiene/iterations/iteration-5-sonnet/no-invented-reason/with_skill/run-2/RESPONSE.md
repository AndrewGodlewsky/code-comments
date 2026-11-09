The session idle timeout is now 15 minutes instead of 30.

Changes:
- `auth/settings.py`: `IDLE_TIMEOUT_MINUTES` is now 15.
- `auth/sessions.py`: the module docstring said 30 minutes, so I changed it to 15.
- `docs/security.md`: the line about idle sessions now says 15 minutes.

I didn't run any tests.

I didn't add a comment explaining why the timeout changed, because nothing in the repository or your request gives a reason. If you tell me the reason, such as a security requirement or a policy, I can record it next to the setting.
