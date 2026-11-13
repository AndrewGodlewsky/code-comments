# Password reset by emailed link: design

```
A. REQUEST FLOW      POST /forgot-password {email}

 Client            API                    Postgres                 Email queue   Email worker
   |  email          |                       |                          |             |
   |---------------->|  find user by email   |                          |             |
   |                 |---------------------->|                          |             |
   |                 |                                                  
   |                 |-- not found ----------------------------------------> (nothing sent)
   |                 |                       |                          |             |
   |                 |  found: BEGIN; lock user row (FOR UPDATE)        |             |
   |                 |---------------------->|                          |             |
   |                 |  count resets for user with created_at > now()-1h |             |
   |                 |<----------------------|                          |             |
   |                 |                                                  
   |                 |-- count >= 3 ---------- ROLLBACK ---------------> (no row, no job)
   |                 |                       |                          |             |
   |                 |  count < 3:                                      |             |
   |                 |   1. set used_at=now() on this user's unused rows|             |
   |                 |      (earlier links die now)                     |             |
   |                 |   2. INSERT password_resets(user_id, created_at, |             |
   |                 |      token_hash=NULL, expires_at=NULL)           |             |
   |                 |   COMMIT                                         |             |
   |                 |---------------------->|                          |             |
   |                 |  enqueue job {reset_id}  (no token in the job)   |             |
   |                 |------------------------------------------------->|             |
   |  200 generic    |                                                  |             |
   |<----------------|  "If an account exists for that address,         |             |
   |                 |   we've sent a link."   (same for ALL paths)     |             |
   |                                                                    |  job        |
   |                                                                    |------------>|
   |                                  worker: if row.used_at set -> skip (superseded)
   |                                  token = 32 random bytes
   |                       UPDATE password_resets SET token_hash=SHA256(token),
   |                         expires_at=now()+30min WHERE id=reset_id AND used_at IS NULL
   |                       send mail with link /reset?token=<raw token> via provider
   |                                  send fails -> retry x3 w/ backoff (re-mints token)
   |                                  still fails -> log + drop (see failure paths)


B. LINK-CLICK FLOW

 Client                      API                                    Postgres
   | GET /reset?token=T       |                                        |
   |------------------------->| h = SHA256(T)                          |
   |                          | SELECT ... WHERE token_hash=h          |
   |                          |   AND used_at IS NULL                  |
   |                          |   AND expires_at > now()   (read only) |
   |                          |--------------------------------------->|
   |   no match / expired /   |                                        |
   |   used                   |                                        |
   |<-------------------------|  "This link has expired, request a     |
   |                          |   new one" page (links to Forgot form) |
   |   match                  |                                        |
   |<-------------------------|  "Choose a new password" page (form carries T)
   |
   | POST /reset {token T, new_password}
   |------------------------->| 1. validate password: len >= 12 AND not in breached list
   |   rejected               |    -> re-show form with reason; NOTHING written,
   |<-------------------------|       link stays usable until it expires
   |                          | 2. BEGIN
   |                          |    UPDATE password_resets SET used_at=now()
   |                          |      WHERE token_hash=SHA256(T) AND used_at IS NULL
   |                          |        AND expires_at > now()  RETURNING user_id
   |                          |      0 rows -> ROLLBACK -> "link has expired" page
   |                          |    UPDATE users SET password_hash=<new hash>
   |                          |    UPDATE password_resets SET used_at=now()
   |                          |      WHERE user_id=.. AND used_at IS NULL
   |                          |    DELETE FROM sessions WHERE user_id=..  (all devices)
   |                          |    COMMIT
   |                          |--------------------------------------->|
   |                          | enqueue "your password was changed" email
   |  302 -> /login           |   (no session created, no auto-login)
   |<-------------------------|


C. FAILURE PATHS

 Where                              What happens
 ---------------------------------  ------------------------------------------------
 Unknown email                      Generic 200, no row, no mail
 Over 3 requests in rolling hour    Generic 200, no row, no mail, old link unchanged
 DB error in request txn            Rolled back; return generic 200 (log it), no mail
 Enqueue fails after commit         Row exists, no job; log. Old links already dead.
                                    User re-requests (counts toward the limit)
 Mail send fails 3x                 Job dropped, logged, nobody told. User still saw the
                                    generic message. Row is inert (expires, never
                                    delivered). User must re-request; this uses quota
 Token missing/wrong/expired/used   "Link has expired" page, on load and on submit
 Two submits race on one token      Conditional UPDATE lets only one win; loser gets
                                    the expired page
 Password too short / breached      Form error, link stays usable until expiry
 Breach-list lookup unavailable     Reject with "try again"; fail closed; link stays
                                    usable, no write
 Txn fails during reset             Whole txn rolls back (token not burned, hash and
                                    sessions untouched); show error, user can retry
 "Password changed" mail fails      Reset already succeeded; job retried, then dropped
```

## Notes

**Data stored.** One new table, `password_resets(id, user_id, token_hash, created_at, expires_at, used_at)`.
- `token_hash` is unique and null until the worker mints the token. It holds only the SHA-256 hash.
- `used_at` is set when a link is burned or superseded. A single column covers both cases.
- `users` and `sessions` need no new columns.

**Raw token never stored.**
- The API job carries only `reset_id`. The worker generates the 32 random bytes, stores the hash and puts the raw token in the email.
- This keeps the raw token out of Postgres, the queue and the logs. Don't log the full link URL.

**Rate limit.**
- The limit counts `password_resets` rows with `created_at` in the last hour. Used and expired rows count too, so rows must stay for at least an hour (purge after about 24h).
- The `FOR UPDATE` lock on the user row makes the count, the invalidation and the insert atomic. Concurrent requests can't slip past the limit of 3.

**Earlier links die at request time.**
- The request transaction invalidates them, not the worker. "Immediately" therefore holds even if the mail queue is backed up.
- The cost is that a failed send leaves the user with no working link until they request again.

**30-minute expiry** starts when the worker mints the token, which is when the link is issued. A queue delay doesn't eat into the user's window. A retry mints a fresh token and overwrites the hash, so only the last token sent can work.

**Burning the link.**
- The conditional `UPDATE ... WHERE used_at IS NULL AND expires_at > now() RETURNING` is the single gate for the check and the burn. It is also the re-check at submit.
- The page-load check is read-only and never burns the token, so email scanners that prefetch the link can't use it up.
- Password validation runs before the transaction. A rejected password therefore never burns the link.

**Logout everywhere** is `DELETE FROM sessions WHERE user_id = ...` in the same transaction as the hash change. This includes the device that did the reset. The API checks `sessions` on every request, so existing logins stop working immediately.

**Open gap: silent drops.**
- The existing worker drops a failed reset email after 3 retries and tells nobody. We can't notify the user, because that would reveal that the account exists.
- At minimum, log the drop with `reset_id` and emit a metric, so a provider outage is visible to us.
- A failed send still counts toward the user's 3-per-hour limit.

**Hardening, no extra storage.**
- Serve `/reset` with `Referrer-Policy: no-referrer`.
- Do the same amount of work before the response on every path (the enqueue is async). That keeps response timing from revealing which addresses exist.
