I raised the idle session timeout from 15 to 30 minutes. A session now stays open until 30 minutes pass without a request, and each request restarts the timer.

Changes:
- `auth/settings.py`: `SESSION_TTL_S` is now `1800` (was `900`).
- `auth/sessions.py` and `auth/views.py`: docstrings updated from fifteen to thirty minutes.
- `docs/security.md`: the idle-session rule now says 30 min.

I left the other 15-minute values alone because they are separate settings: password-reset links (`RESET_LINK_TTL_S`), and the access-token lifetime set by the company identity provider, which this service does not control. If the identity provider's token lifetime is also what is signing admins out mid-edit, that team would need to change it.

The unit tests pass (4 of 4).
