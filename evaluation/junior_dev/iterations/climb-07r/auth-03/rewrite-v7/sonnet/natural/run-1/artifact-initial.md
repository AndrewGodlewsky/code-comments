```
PASSWORD RESET BY EMAILED LINK

Stores:  Postgres users, sessions (existing)
         + password_reset_tokens(token_hash PK, user_id, created_at,
                                 expires_at = created_at+30m, consumed_at NULL)
         Raw token is never stored. consumed_at is set on use OR when
         superseded. Rows are kept for at least 1 hour, because the rate
         limit counts them.

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

## Notes

**Data.** One new table does everything. The rate limit is the count of the account's rows created in the last hour. Over-limit requests insert nothing, so each row is exactly one email. Superseded and used links are marked `consumed_at`, not deleted, so they still count toward the limit. A periodic cleanup can delete rows older than a day.

**Concurrency.** The row lock on `users` in step A makes count, supersede and insert one serial unit. Two simultaneous requests therefore cannot both slip under the limit or leave two live links. In step C the conditional `UPDATE ... RETURNING` makes "works once" hold even if the form is double-submitted. The password change, session deletion and token burn commit together, or not at all.

**Link checks.** The page load is a courtesy check. The submit check in step C is the one that counts. A link superseded or expired while the form is open fails at submit, and the user sees the expired page.

**Failure paths.**

| Failure | Behaviour |
|---|---|
| Unknown email, or over the 3-per-hour limit | Generic reply, nothing created, nothing sent. |
| Invalid, expired, used or superseded token (load or submit) | "This link has expired, request a new one" page. |
| Password too short or breached | Form redisplayed with the reason. Link stays valid until expiry. |
| Breached-list check unavailable | Treat as a failure: ask the user to retry. Never accept an unchecked password. The link stays usable. |
| DB error in step C | Whole transaction rolls back. Password unchanged, link still usable, user sees a generic error. |
| Enqueue fails after the commit in step A | Log it. The user still sees the generic reply. They can request again, and the orphaned row counts toward the limit. |
| Mail send fails 3 times (existing worker) | The job is dropped and nobody is told, so the user never receives a link. They can re-request, and a new link supersedes the dead one. This silent drop is the known gap, and I'm leaving the worker unchanged. If failed sends for reset emails turn out to matter, add an alert on the worker's drop log. |
| Enqueue of the "password changed" email fails | Log it. The reset has already succeeded and is not undone. |

**Security details.**
- The raw token exists only in the link. It lives briefly in the queued job payload, because the worker has to send it. Keep job payloads and send-failure logs free of it, and drop the job when done.
- Send the reset page with `Referrer-Policy: no-referrer` so the token does not leak to third parties.
- Compare hashes by indexed lookup on `token_hash`. No raw-token comparison is needed.
- Do the user lookup and the response so that known and unknown addresses are indistinguishable. The email send is already asynchronous, so response time should not differ much.