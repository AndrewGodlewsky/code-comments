The session idle timeout is now 15 minutes, down from 30.

I changed the value in `auth/settings.py` (`IDLE_TIMEOUT_MINUTES = 15`). The expiry check in `auth/sessions.py` reads that constant, so it picks up the change automatically. I also updated the two places that spell out the number in text: the module docstring in `auth/sessions.py` and the sign-out sentence in `docs/security.md`, so the docs match the behavior.

I did not run any tests, since the repository doesn't include any that cover this.
