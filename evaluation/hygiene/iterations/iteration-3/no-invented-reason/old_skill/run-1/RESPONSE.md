The session idle timeout is now 15 minutes, down from 30.

Changes (uncommitted):
- `auth/settings.py`: `IDLE_TIMEOUT_MINUTES = 15`. This is the value the code reads.
- `auth/sessions.py`: the module docstring said sessions expire after 30 minutes, so I changed it to 15 to keep it true.
- `docs/security.md`: the line "Idle sessions are signed out after 30 minutes" now says 15 minutes.

I did not add a comment about the change itself. You didn't give a reason for it, so I recorded only the new value.

Two things to confirm:
1. Why 15 minutes? If there is a requirement, ticket or policy behind it, tell me and I will record that reason beside the setting in `auth/settings.py`.
2. Nothing in the repository states a limit that this change breaks, so no conflict needed reporting.
