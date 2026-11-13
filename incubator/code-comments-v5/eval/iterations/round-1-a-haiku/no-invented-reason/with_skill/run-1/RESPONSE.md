I changed the session idle timeout from 30 minutes to 15.

Changes:
- `auth/settings.py`: `IDLE_TIMEOUT_MINUTES` is now `15`. This is the only value that controls the timeout; `auth/sessions.py` reads it.
- `auth/sessions.py`: the module docstring said sessions expire after 30 minutes. It now says 15 so it matches the code.
- `docs/security.md`: the note said idle sessions are signed out after 30 minutes. It now says 15.

No comment or doc in these files gives a reason for the 30-minute value, and I found no ticket, test or review that explains it. I also have no reason for the change to 15. I recorded only the new value and did not invent a rationale. Could you tell me why the timeout is moving to 15 minutes, and whether a ticket tracks it? If you give me the reason, I will add it beside the constant in `auth/settings.py`.

I could only check the four files you provided. I did not find other callers or tests in them, so anything outside these files that depends on the 30-minute value is unverified. Please check for other references to the 30-minute value, such as tests or configuration, before you ship.
