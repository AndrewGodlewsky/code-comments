Raised the idle session timeout from 15 to 30 minutes by changing `SESSION_TTL_S` from 900 to 1800 in `auth/settings.py`. I did not run the tests.

I also corrected every statement that still described the old 15-minute behaviour:
- `auth/sessions.py` module docstring and `auth/views.py` `sign_in` docstring now say thirty minutes.
- `auth/forms.py` module docstring said "a quarter of an hour"; it now says "half an hour".
- `docs/security.md` now says idle sessions end after 30 min.
- `docs/console.md` said the "Still there?" banner appears after 14 minutes. The banner shows 60 seconds before the session ends (`IDLE_WARNING_S`), so it now says 29 minutes.

Left unchanged on purpose:
- Password-reset links (`RESET_LINK_TTL_S`), the 15-failed-sign-in lockout, and the 15-minute access tokens in `docs/security.md`. They share the number 15 but are separate settings.

Please check one conflict. `docs/security.md` says access tokens from the company identity provider last 15 minutes, and that the identity team sets that lifetime, not this service. I kept that statement as written. If those tokens are what actually authorise requests, admins could still be cut off at 15 minutes regardless of this change. Please confirm with the identity team whether the token lifetime also needs to rise, or whether tokens are refreshed.

No reason for the change was given beyond the sign-outs during long edits, so I recorded only the new value and added no rationale comment. If there is a ticket or a requirement behind 30 minutes, tell me and I can add it where it belongs.
