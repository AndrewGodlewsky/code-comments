# Password reset by emailed link: design

A user who cannot log in enters their email address and gets a one-time link for choosing a new password. Today, the web client talks to the API server. Postgres holds `users` (with the password hash) and `sessions` (one row per logged-in device, checked on every request). Mail goes through an email queue: the API adds a job, and an email worker sends it through a third-party mail provider. If a send fails, the worker retries 3 times with backoff, then logs the failure and drops the job. Nobody is told.

The flow has two parts. First, the user asks for a link: the API records a reset row in one transaction, and the worker later creates the secret token and emails it. Second, the user clicks the link and submits a new password: one transaction checks the token, burns it, changes the password and ends every session. The token is created by the worker, not the API, so the raw token never sits in Postgres, the queue or the logs.

## Terms

- **Reset row**: one row in the new `password_resets` table. It stands for one issued link.
- **Token**: 32 random bytes. It appears only inside the emailed link.
- **Token hash**: the SHA-256 of the token. It is the only form we store.
- **Burned**: a link that can no longer be used. We mark it by setting `used_at`. This one column covers both "used" and "replaced by a newer link".
- **Generic message**: "If an account exists for that address, we've sent a link." Every outcome of the request step returns it.

## Data

One new table: `password_resets(id, user_id, token_hash, created_at, expires_at, used_at)`.
- `token_hash` is unique. It is null until the worker creates the token.
- `users` and `sessions` need no new columns.

## How it runs

```
A. REQUEST FLOW      POST /forgot-password {email}

 Client            API                    Postgres                 Email queue   Email worker
   |  email          |                       |                          |             |
   |---------------->|  find user by email   |                          |             |
   |                 |---------------------->|                          |             |
   |                 |-- not found ----------------------------------------> (nothing sent)
   |                 |  found: BEGIN; lock user row (FOR UPDATE)        |             |
   |                 |  count this user's resets with created_at > now()-1h           |
   |                 |-- count >= 3 ---------- ROLLBACK ---------------> (no row, no job)
   |                 |  count < 3:                                      |             |
   |                 |   1. burn this user's unused rows (set used_at)  |             |
   |                 |   2. INSERT reset row (token_hash=NULL,          |             |
   |                 |      expires_at=NULL)                            |             |
   |                 |   COMMIT                                         |             |
   |                 |  enqueue job {reset_id}   (no token in the job)  |             |
   |                 |------------------------------------------------->|             |
   |  200 generic    |                                                  |             |
   |<----------------|  (same message and same work for ALL paths)      |------------>|
   |                                                                    |             |
   |                       worker: if the row is already burned -> skip |             |
   |                       token = 32 random bytes                      |             |
   |                       UPDATE reset row SET token_hash=SHA256(token),             |
   |                         expires_at=now()+30min WHERE id=reset_id AND used_at IS NULL
   |                       email link /reset?token=<token> via provider |             |
   |                       send fails -> retry up to 3x (each retry makes a new token) |
   |                       still fails -> log reset_id, emit metric, drop job


B. LINK-CLICK FLOW

 Client                      API                                    Postgres
   | GET /reset?token=T       |                                        |
   |------------------------->| SELECT reset row WHERE                 |
   |                          |   token_hash=SHA256(T) AND used_at IS NULL
   |                          |   AND expires_at > now()  (read only)  |
   |   no match               |                                        |
   |<-------------------------|  "This link has expired, request a new one" page
   |   match                  |                                        |
   |<-------------------------|  "Choose a new password" form (carries T)
   |
   | POST /reset {T, new_password}
   |------------------------->| 1. check password: >= 12 chars and not on the breached list
   |   rejected               |    -> show form again with the reason; nothing written;
   |<-------------------------|       link stays usable until it expires
   |                          | 2. BEGIN
   |                          |    UPDATE reset row SET used_at=now()
   |                          |      WHERE token_hash=SHA256(T) AND used_at IS NULL
   |                          |        AND expires_at > now()  RETURNING user_id
   |                          |      0 rows -> ROLLBACK -> "link has expired" page
   |                          |    UPDATE users SET password_hash=<new hash>
   |                          |    burn all of this user's other unused rows
   |                          |    DELETE FROM sessions WHERE user_id=..  (all devices)
   |                          |    COMMIT
   |                          | enqueue "your password was changed" email
   |  302 -> /login           |   (no session is created; no auto-login)
   |<-------------------------|
```

**Notes on the request flow**
- **Why the lock.** `FOR UPDATE` on the user row makes the count, the burn and the insert one atomic step. Two concurrent requests cannot both slip under the limit of 3.
- **Why the count includes burned and expired rows.** The limit is 3 reset emails in any rolling hour, so every row counts. Keep rows at least an hour; purge after about 24 hours.
- **Why old links die here, not in the worker.** "Immediately" must hold even if the queue is backed up. The cost: if a send fails, the user has no working link until they request again.
- **Why the worker makes the token.** The raw token stays out of Postgres, the queue and the logs. Never log the full link URL.
- **When the 30 minutes start.** When the worker creates the token, so queue delay does not shorten the user's window. A retry makes a new token and overwrites the hash, so only the last token sent works.
- **Why the response looks the same on every path.** Same message, same amount of work before replying (the enqueue is async). Timing then does not reveal which addresses exist.

**Notes on the link-click flow**
- The page-load check is read-only and never burns the token, so email scanners that prefetch the link cannot use it up.
- The conditional `UPDATE ... RETURNING` is the single gate at submit. It checks and burns in one statement. If two submits race, only one wins; the other sees the expired page.
- Password checks run before the transaction, so a rejected password never burns the link.
- Deleting the user's `sessions` rows in the same transaction logs out every device, including the one that did the reset. The API checks `sessions` on every request, so old logins stop at once.
- Serve `/reset` with `Referrer-Policy: no-referrer`.

## What happens when things fail

```
C. FAILURE PATHS

 Where                              What happens
 ---------------------------------  ------------------------------------------------
 Unknown email                      Generic 200, no row, no mail
 Over 3 requests in rolling hour    Generic 200, no row, no mail; earlier link unchanged
 DB error in request transaction    Rolled back; log it; generic 200; no mail
 Enqueue fails after commit         Row exists, no job; log it. Earlier links are already
                                    dead. User must request again (counts toward limit)
 Mail send fails 3x                 Job dropped, logged, metric emitted. User saw the
                                    generic message. Row never gets delivered and just
                                    expires. User must request again (counts toward limit)
 Token missing/wrong/expired/used   "Link has expired" page, on load and on submit
 Password too short or breached     Form error; link stays usable until it expires
 Breach-list lookup unavailable     Reject with "try again"; nothing written; link stays
                                    usable (fails closed)
 Transaction fails during reset     Whole transaction rolls back (link not burned, hash and
                                    sessions untouched); show error; user can retry
 "Password changed" mail fails      Reset already succeeded; the job is retried, then dropped
```

## Open questions

- **Silent drops.** The existing worker drops a failed reset email after 3 retries and tells nobody. We cannot notify the user, because that would reveal the account exists. The minimum is the log line with `reset_id` and a metric, so we can see a provider outage. Nothing yet gives the affected user a way forward except requesting again.
