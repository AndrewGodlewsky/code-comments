I raised the idle session timeout from 15 to 30 minutes. A session now stays open until 30 minutes pass without a request, so admins who pause during long edits should no longer be signed out.

Changes:
- `auth/settings.py`: `SESSION_TTL_S` changed from 900 to 1800 seconds. This is the only value the session check reads.
- `auth/sessions.py` and `auth/views.py`: docstrings updated from "fifteen minutes" to "thirty minutes".
- `docs/security.md`: idle session rule updated from 15 to 30 minutes.

I left two other 15-minute settings alone because they are separate rules. Password-reset links still expire after 15 minutes (`RESET_LINK_TTL_S`). Access tokens from the identity provider still last 15 minutes, and that lifetime is set by the identity team.

The unit tests pass (4 of 4). They read the setting rather than a hard-coded number, so they still pass at the new value.
