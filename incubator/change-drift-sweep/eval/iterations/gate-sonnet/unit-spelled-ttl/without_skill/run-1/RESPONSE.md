I raised the idle session timeout from 15 to 30 minutes by setting `SESSION_TTL_S` to 1800 in `auth/settings.py`.

I also updated the places that spelled out the old value, so they don't contradict the code:
- the module docstring in `auth/sessions.py`
- the docstring in `auth/views.py`
- the Sessions section of `docs/security.md`

The password-reset link expiry (`RESET_LINK_TTL_S`, 15 minutes) is a separate setting and I left it unchanged. The existing tests reference the setting rather than a hard-coded number, so they needed no edits.
