The session idle timeout is now 15 minutes instead of 30.

I changed the value in `auth/settings.py` (`IDLE_TIMEOUT_MINUTES = 15`). Two other places stated the old 30-minute figure, so I updated them too:

- `auth/sessions.py`: the module docstring now says sessions expire after 15 minutes without a request.
- `docs/security.md`: now says idle sessions are signed out after 15 minutes.

The existing comment on `IDLE_TIMEOUT_MINUTES` is still accurate and was left alone. I did not run any tests, and the changes are uncommitted.
