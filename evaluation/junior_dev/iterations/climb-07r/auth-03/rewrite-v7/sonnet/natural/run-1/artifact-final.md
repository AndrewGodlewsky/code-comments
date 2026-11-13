PASSWORD RESET BY EMAILED LINK

A user who cannot log in enters their email and receives a one-time link that lets them set a new password. Today the web client calls the API server, which keeps users and sessions in Postgres and sends mail by adding a job to an email queue. The reset adds one table of hashed, single-use, 30-minute tokens. All checks that must not race (the rate limit, "works once") are done inside Postgres transactions, so no new lock service or queue is needed.

Terms
- Token: 32 random bytes. It appears only inside the emailed link. Only its SHA-256 hash is stored.
- password_reset_tokens: the one new table. Columns: token_hash (primary key), user_id, created_at, expires_at (= created_at + 30 min), consumed_at (NULL while the link is usable).
- Consumed: consumed_at is set, either because the link was used or because a newer link replaced it ("superseded"). Rows are never deleted on use, because the rate limit counts them.
- sessions: existing table, one row per logged-in device. The API checks it on every request, so deleting a user's rows logs them out everywhere.
- Email queue / worker: existing. The API adds a job. The worker sends it through the third-party mail provider, retries up to 3 times with backoff, then logs the failure and drops the job. Nobody is notified. This worker is not changed.
- Breached-password list: an external list of known leaked passwords. A new password must not be on it.

```
=== A. REQUEST ("Forgot password?") ======================================

 Browser            API server                Postgres        Email queue/worker
    | POST /forgot {email}                        |                  |
    |------------------>|                         |                  |
    |                   | BEGIN; find user by email                  |
    |                   |------------------------>|                  |
    |                   |<-- no user -------------|                  |
    |                   |    (COMMIT; skip to reply: nothing sent)   |
    |                   | user found: SELECT ... FOR UPDATE on user row
    |                   |   (serializes concurrent requests)         |
    |                   | count tokens WHERE user_id AND             |
    |                   |   created_at > now()-1h                    |
    |                   |------------------------>|                  |
    |                   |<-- n ------------------|                  |
    |                   | n >= 3 ? COMMIT, skip to reply:            |
    |                   |   no token, no email                       |
    |                   | n < 3:                                     |
    |                   |   token = 32 random bytes                  |
    |                   |   UPDATE earlier rows SET consumed_at=now()|
    |                   |     WHERE user_id AND consumed_at IS NULL  |
    |                   |   INSERT (sha256(token), user_id, ...)     |
    |                   |   COMMIT                                   |
    |                   | enqueue "reset" job (link with raw token)  |
    |                   |----------------------------------------->  |
    |                   |                                  worker -> mail provider
    |<-- 200 "If an account exists for that address,         (retry x3, then
    |         we've sent a link."  (identical in ALL cases)   log + drop)

=== B. LINK CLICK (page load) ============================================

 Browser: GET /reset?token=T  (Referrer-Policy: no-referrer)
   API: h = sha256(T)
        SELECT FROM password_reset_tokens
          WHERE token_hash=h AND consumed_at IS NULL AND expires_at > now()
        |-- no row (invalid / expired / used / superseded)
        |        --> "This link has expired, request a new one" page
        |            (links to the Forgot password form)
        '-- row found --> "Choose a new password" form (token kept in the
                          form; the page load does NOT consume the link)

=== C. FORM SUBMIT =======================================================

 Browser: POST /reset {token T, new password}
   API: 1. len >= 12 ?  not on breached list ?
           |-- no  --> redisplay form with the reason; token untouched,
           |           link stays usable until it expires
           '-- yes
        2. h = sha256(T); BEGIN
             UPDATE password_reset_tokens SET consumed_at=now()
               WHERE token_hash=h AND consumed_at IS NULL
                 AND expires_at > now()
               RETURNING user_id        <-- the atomic re-check; one winner
             |-- 0 rows --> ROLLBACK --> "link has expired" page
             '-- 1 row:
                UPDATE users SET password_hash=hash(new) WHERE id=user_id
                DELETE FROM sessions WHERE user_id=user_id   (all devices,
                                                 including this one)
             COMMIT
        3. enqueue "your password was changed" email
        4. clear session cookie; 302 --> /login   (no auto login)
```

Notes on the diagram

Rules (each applies at the step shown)
- Step A: the reply is always "If an account exists for that address, we've sent a link." Unknown addresses get it too, and nothing is sent to them.
- Step A: at most 3 reset emails per account in any rolling hour. Over the limit, the reply is the same, but no link is created and no email is sent. Because over-limit requests insert nothing, each row is exactly one email, and the rate limit is simply the count of the account's rows created in the last hour.
- Step A: issuing a new link marks every earlier unused link consumed, so only the newest link works.
- Steps A and C: a link is valid for 30 minutes and works once.
- Step C: the new password must be at least 12 characters and not on the breached list. If it is rejected, the link stays usable and the user can retry until it expires.
- Step C: on success, the user is logged out everywhere, gets a "your password was changed" email, and is sent to the login page without being logged in.

Why it is shaped this way
- The row lock on the user in step A makes count, supersede and insert one serial unit. Two simultaneous requests cannot both slip under the limit or leave two live links.
- The page load in step B is only a courtesy check. The conditional UPDATE ... RETURNING in step C is the check that counts: it makes "works once" hold even if the form is double-submitted, and it rejects a link that expired or was superseded while the form was open. The password change, session deletion and token burn commit together or not at all.
- Rows are kept at least 1 hour because the rate limit counts them. A periodic cleanup can delete rows older than a day.

Security
- The raw token lives briefly in the queued job payload, because the worker must send it. Keep job payloads and send-failure logs free of it, and drop the job when done.
- The reset page is sent with Referrer-Policy: no-referrer so the token does not leak to third parties.
- Lookup is by hash on the indexed token_hash column, so no raw-token comparison is needed.
- Known and unknown addresses must look the same. The email send is already asynchronous, so response time should not differ much.

What happens when things fail

| Failure | Behaviour |
|---|---|
| Unknown email, or over the 3-per-hour limit | Generic reply, nothing created, nothing sent. |
| Invalid, expired, used or superseded token (load or submit) | "This link has expired, request a new one" page. |
| Password too short or breached | Form redisplayed with the reason. Link stays valid until expiry. |
| Breached-list check unavailable | Treated as a failure: ask the user to retry. Never accept an unchecked password. The link stays usable. |
| DB error in step C | Whole transaction rolls back. Password unchanged, link still usable, user sees a generic error. |
| Enqueue fails after the commit in step A | Log it. The user still sees the generic reply. They can request again, and the orphaned row counts toward the limit. |
| Mail send fails 3 times (existing worker) | The job is dropped and nobody is told, so the user never receives a link. They can re-request, and the new link supersedes the dead one. |
| Enqueue of the "password changed" email fails | Log it. The reset has already succeeded and is not undone. |

Open questions
- Silent drop of failed reset emails is a known gap, and the worker is left unchanged. If failed sends for reset emails turn out to matter, add an alert on the worker's drop log.