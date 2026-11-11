The idle session timeout is now 30 minutes, up from 15. Admins should no longer be signed out in the middle of long edits.

What changed:
- `auth/settings.py`: `SESSION_TTL_S` is now `1800`. The "Still there?" banner still appears 60 seconds before the session ends.
- `docs/security.md`: the sessions section now says 30 min.
- `auth/sessions.py` and `auth/forms.py`: docstrings updated from fifteen minutes and a quarter of an hour to thirty minutes and half an hour.

The unit tests pass (6 of 6). They read the timeout from settings, so they cover the new value.

One thing to check: `docs/security.md` says access tokens from the company identity provider last 15 minutes, and the identity team sets that lifetime. If a token expiry also ends an admin's session, the 30-minute idle timeout will not fully fix the sign-outs. That lifetime is not in this repository, so I did not change it. The identity team would need to confirm whether it applies here.

The password-reset link lifetime (15 minutes) is unchanged because it is a separate setting.
