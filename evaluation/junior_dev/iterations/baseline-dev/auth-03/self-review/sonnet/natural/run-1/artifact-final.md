# Password reset by emailed link

```
SYSTEM (all exists today except the password_resets table)
  Browser --> API server --> Postgres: users, sessions, NEW password_resets
              API server --> email queue --> email worker --> third-party mail provider

NEW TABLE
  password_resets(id, user_id, token_hash UNIQUE, issued_at, expires_at, used_at NULL)
  - One row per issued link. Only sha256(token) is stored, never the token itself.
  - used_at is set when the link is used OR replaced by a newer link.
    "Live" link = used_at IS NULL and expires_at > now.
  - Rows are kept after use, so "resets in the last hour"
    = this user's rows with issued_at > now - 1 hour.

DEFINITIONS
  h           = sha256(token from the URL or form)
  token check = SELECT the row WHERE token_hash = h. The token is valid only if
                the row exists, used_at IS NULL and expires_at > now.
                Otherwise it is invalid (missing, used, replaced or expired).

=== A. REQUEST:  POST /forgot-password {email} ================================

Browser                 API server                      Postgres / email queue
  | email                  |
  |----------------------->|
  |<-----------------------| 200 "If an account exists for that address,
  |                        |      we've sent a link."  (identical every time,
  |                        |       sent before any lookup)
  |                        | Then, after replying:
  |                        | 1. Find user by email.
  |                        |      none -> stop. Nothing is sent.
  |                        | 2. BEGIN; lock the user row (SELECT ... FOR UPDATE).
  |                        | 3. count = this user's rows with issued_at in the
  |                        |      last hour (including used or replaced rows).
  |                        |      count >= 3 -> ROLLBACK, stop. No link, no email.
  |                        | 4. token = 32 random bytes.
  |                        | 5. UPDATE password_resets SET used_at = now
  |                        |      WHERE user_id = ? AND used_at IS NULL
  |                        |      (kills the user's earlier unused link)
  |                        | 6. INSERT (user_id, sha256(token), now, now + 30 min).
  |                        | 7. COMMIT.
  |                        | 8. Add email job {to, link containing raw token}
  |                        |      to the email queue.

Email worker (existing behaviour): send via the mail provider. On failure, retry
up to 3 times with backoff. Still failing -> log it and drop the job. Nobody is
told (see Failure paths).

=== B. LINK CLICK:  GET /reset?token=...   (read-only; never uses up the link) ==

Browser                 API server                      Postgres
  | GET link               |
  |----------------------->| h = sha256(token); token check -->
  |                        |
  |                        | Invalid:
  |<-----------------------|   page "This link has expired, request a new one"
  |                        |   (links to "Forgot password?")
  |                        | Valid:
  |<-----------------------|   "Choose a new password" form (token kept in a
  |                        |   hidden form field)

=== C. SUBMIT:  POST /reset {token, new_password} ==============================

Browser                 API server                      Postgres
  | token + password       |
  |----------------------->| 1. Token check, as in B.
  |                        |      invalid -> expired page.
  |                        | 2. Check the password: under 12 characters, or on
  |<-----------------------|      the breached list -> form again with an error.
  |                        |      Nothing changes; link stays usable until it
  |                        |      expires.
  |                        | 3. BEGIN
  |                        |    UPDATE password_resets SET used_at = now
  |                        |      WHERE token_hash = h AND used_at IS NULL
  |                        |        AND expires_at > now
  |                        |      RETURNING user_id
  |                        |      0 rows (another submit won, or the link just
  |                        |      expired) -> ROLLBACK, expired page.
  |                        |    UPDATE users SET password_hash = hash(password)
  |                        |      WHERE id = user_id
  |                        |    DELETE FROM sessions WHERE user_id = user_id
  |                        |      (every device, including this one)
  |                        |    COMMIT
  |                        | 4. Add job "your password was changed"
  |                        |      to the email queue.
  |<-----------------------| 5. 302 redirect to /login (no session is created).
```

## Notes

**Same response in A, whatever happens.** Unknown address, rate-limited and sent all get the same message and status. The reply goes out before the lookup, so response time cannot reveal whether an account exists.

**Rate limit and "kill the old link" are race-safe.** Step 2 locks the user's row, so concurrent requests for the same account run one at a time. Two requests cannot both pass the limit of 3, and there is never more than one live link per account. Replaced rows keep their `issued_at`, so they still count toward the hour.

**Token handling.** Only `sha256(token)` is stored. The raw token exists in API memory, in the email job (inside the link) and in the email itself. Do not log job payloads, and delete the job once it is sent or dropped. Serve the reset page with `Referrer-Policy: no-referrer` so the token does not leak to other sites.

**GET never uses up the link.** Mail scanners and link previewers fetch URLs automatically. Only a successful POST sets `used_at`, through a conditional UPDATE (`used_at IS NULL`), so the link works exactly once even if two submits arrive together.

**Expiry.** The 30 minutes are enforced by `expires_at > now` on both page load and submit, so no cleanup is needed for correctness. A periodic job deletes rows older than a day to keep the table small. The rate limit only looks back one hour, so this does not affect it.

**One transaction for link, password and sessions.** Burning the link, changing the password and deleting sessions commit together. If the process died between separate writes, you could get a new password with old devices still logged in, or a burned link with no password change.

**Failure paths**

| Failure | Result |
|---|---|
| Token invalid, expired or used (at load or at submit) | Expired page. The user requests a new link. |
| Password too short or breached | Form with an error. Link is not used up and can be retried until it expires. |
| Breached-list check unavailable | Fail closed: show a "try again" error. Link is not used up. |
| DB error during the submit transaction | Everything rolls back (password, link and sessions unchanged). Show a generic error. The link is still usable. |
| Reset email fails all 3 retries | **Silent today.** The worker drops the job and nobody is told. The user saw the generic message and no email arrives. They can request again, but the failed attempt still counts toward their 3 per hour. Fixing this needs a notification mechanism, which is outside this feature. Follow-up: alert on dropped reset jobs, or have the worker mark the row so it does not count. |
| "Password changed" email fails to enqueue or send | The reset still succeeds, because the email is queued after COMMIT. The lost notice is only logged, with the same silent-drop caveat. |
| Enqueue of the reset job fails in A | The row exists but no email goes out. The user already got the generic message, and the dead row counts toward the limit. Log it. |
