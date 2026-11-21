```
PASSWORD RESET BY EMAILED LINK

Stores (Postgres):
  users(id, email, password_hash)
  sessions(id, user_id, ...)                 -- existing
  password_resets(id, user_id, token_hash UNIQUE,
                  issued_at, expires_at = issued_at + 30m,
                  used_at NULL, killed_at NULL)

=====================================================================
A. REQUEST FLOW   POST /forgot-password {email}
=====================================================================

 Client            API server                    Postgres        Email queue -> worker -> provider
   |  email           |                             |
   |----------------->|                             |
   |                  | normalise email, look up    |
   |                  |---------------------------->| users
   |                  |<----------------------------|
   |                  |
   |                  +-- no such user ------------------------------+
   |                  |                                              |
   |                  +-- user found:                                |
   |                  |     BEGIN txn; lock user row (FOR UPDATE)    |
   |                  |---------------------------->|                |
   |                  |     count password_resets for user           |
   |                  |     WHERE issued_at > now()-1h               |
   |                  |        |                                     |
   |                  |        +-- count >= 3 --> ROLLBACK ----------+
   |                  |        |                  (no row, no job)   |
   |                  |        |                                     |
   |                  |        +-- count < 3:                        |
   |                  |             token = 32 random bytes          |
   |                  |             UPDATE password_resets           |
   |                  |               SET killed_at=now()            |
   |                  |               WHERE user_id=? AND used_at    |
   |                  |               IS NULL AND killed_at IS NULL  |
   |                  |             INSERT row (SHA-256(token),      |
   |                  |               issued_at=now, expires +30m)   |
   |                  |             COMMIT                           |
   |                  |             enqueue "reset" job  ------------------> queue
   |                  |             (link contains raw token;        |   worker sends via provider
   |                  |              token is NOT logged)            |   (retry 3x, then drop: see F4)
   |                  |                                              |
   |  200 "If an account exists for that address,                    |
   |<-------------- we've sent a link."  <---------------------------+
   |   (identical body, status and shape on every branch)

=====================================================================
B. LINK-CLICK FLOW   GET /reset?token=T   and   POST /reset
=====================================================================

 Browser                API server                       Postgres
   | GET /reset?token=T    |
   |---------------------->| h = SHA-256(T); find row by token_hash
   |                       |------------------------------->|
   |                       | valid = row exists AND used_at NULL
   |                       |         AND killed_at NULL AND now < expires_at
   |   valid   <-----------| render "choose a new password" form
   |   invalid <-----------| render "this link has expired, request a new one"
   |                       |   (same page for unknown/expired/used/killed)
   |
   | POST /reset {token T, new password}
   |---------------------->| (CHECK 2: token re-validated)
   |                       | invalid --> "link expired" page, stop
   |                       | password < 12 chars        --> form + error, token untouched
   |                       | password in breached list  --> form + error, token untouched
   |                       |   (user may retry until expiry)
   |                       | BEGIN txn
   |                       |   UPDATE password_resets SET used_at=now()
   |                       |     WHERE id=? AND used_at IS NULL
   |                       |       AND killed_at IS NULL AND now<expires_at
   |                       |     -- 0 rows affected => ROLLBACK, "link expired" page
   |                       |   UPDATE users SET password_hash=hash(new)
   |                       |   DELETE FROM sessions WHERE user_id=?   (all devices,
   |                       |                                  incl. this one)
   |                       | COMMIT
   |                       | enqueue "your password was changed" email --> queue
   |  302 /login  <--------| (no session created; user logs in manually)

=====================================================================
C. FAILURE PATHS
=====================================================================

 F1 Unknown email ........ generic 200, nothing stored or sent.
 F2 Rate limit hit ....... generic 200, no row, no job, earlier link unchanged.
 F3 DB error on request .. txn rolls back; no job enqueued; still return the
                           generic 200 (log + alert; do not leak state).
 F4 Email send fails ..... worker retries 3x with backoff, then drops the job.
                           User sees nothing and may request again (counts
                           toward the 3/hour). Gap: nobody is notified.
 F5 Token bad/expired/used/killed on GET or POST ... "link expired" page.
 F6 Two simultaneous submits of one link ... the conditional UPDATE of
                           used_at lets only one win; loser gets "link expired".
 F7 Weak/breached password ... form re-shown with error; link stays valid.
 F8 DB error on submit .... whole txn rolls back (hash, link and sessions all
                           unchanged); show a generic error, link stays usable.
 F9 "Password changed" email fails ... reset already committed; same retry/drop
                           as F4. The user is still redirected to login.
```

Notes

- **Data:** one new table, `password_resets`. Only the SHA-256 of the token is stored. The raw token exists only in the emailed link and in the queued job payload. The job must not be logged, and it should be deleted once sent or dropped.
- **Rate limit:** the count is over rows issued in the last hour for that user. Each issued link is one row, so no separate counter is needed. The user-row lock stops two parallel requests from both passing the count check. Rate-limited, unknown and sent requests all return the same status, body and shape. Keep their response times similar too, for example by enqueueing the job after replying or without waiting, so the response does not reveal whether the account exists.
- **One live link:** issuing a new link sets `killed_at` on the older unused links in the same transaction that inserts the new one. At most one link per account is ever valid.
- **Single use and expiry:** validity is `used_at IS NULL AND killed_at IS NULL AND now() < expires_at`. The page-load check only decides what to show. The submit check is the authoritative one. The conditional `UPDATE ... used_at` is what actually enforces single use under concurrency.
- **Reset is atomic:** the new hash, the burned link and the deleted sessions commit together. Because the API checks `sessions` on every request, deleting the rows logs out every device immediately, including the one that reset. No session is created afterwards.
- **Rejected passwords:** these are not an attempt that consumes the link. Validation happens before the burn. Do the same check on the server even if the client also checks.
- **Known gap (F4, F9):** the existing worker drops failed jobs silently. A user whose reset email never arrives gets no signal and may hit the 3/hour limit while retrying. The "password changed" email failing means the user may not learn of an unauthorised change. This design does not change the worker. If we want to fix it, the minimum is an alert on dropped reset and password-changed jobs.
- **Housekeeping (optional):** delete `password_resets` rows older than a day. The rate limit only needs the last hour.