## Review of auth-01 (junior-v1, author haiku, natural)

Rounds: 1. Ended: teachback-correct.

### What changed
- Rule 3: states that the fifth wrong password gets 401, the lock is written then, and the sixth attempt gets 429; explains why old failures cannot re-lock the email when the 15-minute lock ends.
- Rule 5: explains that pg_advisory_xact_lock is released at commit or rollback, that a second same-email attempt waits and then sees committed rows, and that a wait past the 2-second timeout returns 503.
- Rule 8: says what happens when there is no cookie or the cookie matches no row, and that a new ID is issued even when the incoming cookie was valid.
- Rule 10: the check needs only user_id; pages needing more user data query by user_id after the check.
- Rule 11: states that the app learns logout intent from the POST itself, that SameSite=Lax stops forged cross-site logouts from destroying anything, and that same-site attackers are not covered.
- Schema: added a foreign key from sessions.user_id to users(id) with ON DELETE CASCADE, so a deleted user cannot keep a live session.
- Notes: added a paragraph on login failing before COMMIT (full rollback, nothing kept) and on a failure during COMMIT (outcome unknown, 503, no cookie, orphan row expires).
- Notes: session lifetime now says that closing the browser does not end the server session and that a restored or copied cookie works until expires_at.
- Added an Open questions line on whether browsers restore session cookies, which is not verified.

### Holes
- None.
