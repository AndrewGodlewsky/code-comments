I raised the idle session timeout from 15 to 30 minutes. `SESSION_TTL_S` in `auth/settings.py` is now 1800. The "Still there?" banner still appears 60 seconds before the end, so it now shows at 29 minutes idle.

I also updated the text that described the old 15-minute timeout so it matches:
- `auth/sessions.py` and `auth/views.py` docstrings now say thirty minutes.
- `auth/forms.py` now says a form left idle for half an hour can no longer be saved.
- `docs/security.md` now says idle sessions end after 30 minutes.
- `docs/console.md` now says the banner appears after 29 minutes without a request.

Left unchanged on purpose: the 15-minute reset-link lifetime, the 15-failed-sign-in lockout, and the 15-minute access-token lifetime in `docs/security.md`. That token lifetime is set by the company identity provider, not this service.

Please check the identity-provider access token. If it expires after 15 minutes, admins could still be signed out mid-edit even with the longer idle timeout. The identity team would need to change that lifetime.

The test suite passes (`python -m unittest`, 6 tests).
