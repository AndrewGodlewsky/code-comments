# Password reset by emailed link

```
DATA (new table; users, sessions, email queue unchanged)
  password_resets(id, user_id, token_hash UNIQUE, issued_at, expires_at, used_at NULL)
  used_at is set when the link is burned OR superseded by a newer link.
  Rows are kept, so the rolling-hour limit is COUNT(*) WHERE issued_at > now()-1h.

=== A. REQUEST FLOW:  POST /forgot-password {email} ============================

Browser           API server                          Postgres        Email queue / worker
   |  email          |                                   |                    |
   |---------------->|                                   |                    |
   |                 | look up user by email ----------->|                    |
   |                 |<-- user or none ------------------|                    |
   |                 |                                                        |
   |                 +-- no user ---------------------------------+           |
   |                 |                                            |           |
   |                 +-- user found:                              |           |
   |                 |   BEGIN; lock user row (FOR UPDATE) ------>|           |
   |                 |   count resets issued in last 1h --------->|           |
   |                 |                                            |           |
   |                 |   count >= 3 ------------------------+    |           |
   |                 |      ROLLBACK, create nothing         |    |           |
   |                 |                                       |    |           |
   |                 |   count < 3:                          |    |           |
   |                 |     token = 32 random bytes           |    |           |
   |                 |     UPDATE password_resets            |    |           |
   |                 |       SET used_at=now                 |    |           |
   |                 |       WHERE user_id=? AND used_at IS NULL (kills old)  |
   |                 |     INSERT (user_id, sha256(token),   |    |           |
   |                 |       now, now+30min)                 |    |           |
   |                 |     COMMIT                            |    |           |
   |                 |     add job {to, link with raw token} ---------------->|
   |                 |                                       |    |           |
   |<----------------+<--------- all four branches converge -+----+           |
   |  200 "If an account exists for that address, we've sent a link."         |
   |                                                                          |
   |                                    worker sends via mail provider        |
   |                                    fail -> retry x3 with backoff         |
   |                                    still failing -> log, drop job (X)    |

=== B. LINK CLICK:  GET /reset?token=...  (read-only, never burns the token) ====

Browser           API server                          Postgres
   |  GET link       |                                   |
   |---------------->| h = sha256(token)                 |
   |                 | SELECT WHERE token_hash=h ------->|
   |                 |<-- row or none -------------------|
   |                 |
   |                 +-- none / used_at set / expires_at < now
   |<----------------+      -> page "This link has expired, request a new one"
   |                 |         (links to Forgot password?)
   |                 +-- valid
   |<----------------+      -> "Choose a new password" form (token kept in form)

=== C. SUBMIT:  POST /reset {token, new_password} ===============================

Browser           API server                          Postgres
   |  token + pw     |
   |---------------->| 1. re-check token as in B ------->|
   |                 |      invalid -> expired page (same as B)
   |                 | 2. pw < 12 chars, or on breached list
   |<----------------+      -> form again with error. NOTHING is burned,
   |                 |         link stays usable until it expires.
   |                 | 3. BEGIN
   |                 |    UPDATE password_resets SET used_at=now
   |                 |      WHERE token_hash=h AND used_at IS NULL
   |                 |      AND expires_at > now RETURNING user_id --->|
   |                 |      0 rows (lost a race / just expired)
   |                 |         -> ROLLBACK, expired page
   |                 |    UPDATE users SET password_hash=hash(pw) ---->|
   |                 |    DELETE FROM sessions WHERE user_id=? ------->|
   |                 |      (every device, including this one)
   |                 |    COMMIT
   |                 | 4. add job "your password was changed" -> email queue
   |<----------------+ 5. 302 -> /login   (no session is created)
```

## Notes

**Same response for every outcome in A.** Unknown address, rate-limited and sent all return the same message and status. Do the same amount of visible work in each branch, for example by enqueuing the email after responding, so response time does not reveal whether an account exists.

**Rate limit and "kill old link" are race-safe.** Locking the user row serializes concurrent requests, so two simultaneous requests cannot both pass the count of 3 or leave two live links. Superseded rows keep their `issued_at`, so they still count toward the hour. Only one link per account is ever live.

**Token handling.** Only `sha256(token)` is stored. The raw token exists in memory in the API, in the email job payload (as the link) and in the email itself. Do not log job payloads, and delete the job once it is sent or dropped. The reset page should send `Referrer-Policy: no-referrer`.

**GET never burns the link.** Mail scanners and link previewers prefetch URLs. Only the successful POST sets `used_at`, and it does so with a conditional UPDATE, so a link works exactly once even with two simultaneous submits.

**Expiry.** The 30 minutes are enforced by `expires_at > now` at both page load and submit. Nothing needs to clean up for correctness. Delete rows older than a day with a periodic job to keep the table small.

**Failure paths.**

| Failure | Result |
|---|---|
| Token invalid, expired or used (at load or at submit) | Expired page. The user requests a new link. |
| Password too short or breached | Form with error. Link is not burned and can be retried until it expires. |
| Breached-list check unavailable | Fail closed: show a "try again" error, link is not burned. |
| DB error during the submit transaction | Everything rolls back (password, link and sessions are unchanged). Show a generic error. The link is still usable. |
| Reset email fails all 3 retries | **Silent today**: the worker drops the job and the user is never told. The user sees the generic message and no email arrives. They can request again, but the dead attempt already counts toward their 3 per hour. Not fixable without notification, which is outside this feature. Worth a follow-up: alert on dropped reset jobs, or have the worker mark the row so it does not count. |
| "Password changed" email fails to enqueue or send | The reset still succeeds, because the email is sent after COMMIT. A lost notice is logged only, with the same silent-drop caveat. |
| Enqueue of the reset job fails in A | The row exists but no email goes out. The user still gets the generic message, and the dead row counts toward the limit. Log it. |

**Why sessions are deleted in the same transaction as the password change.** If the process died between the two, the password would be new while old devices stayed logged in. One transaction avoids that.
