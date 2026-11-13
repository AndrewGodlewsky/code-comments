~~~
PASSWORD RESET BY EMAILED LINK

Data (one new table; reuses users, sessions, email queue)
  password_reset_tokens(token_hash PK, user_id FK, issued_at, expires_at = issued_at+30m,
                        dead_at NULL)   -- dead_at set when used OR superseded. Rows are kept.
  A link is live  <=>  dead_at IS NULL AND expires_at > now()
  Rate limit      =  count(rows for user_id with issued_at > now()-1h)   (no separate counter)

==================== 1. REQUEST FLOW  (POST /forgot-password {email}) ====================

 Web client                API server                              Postgres            Email queue/worker
     |  email                  |                                      |                       |
     |------------------------>|                                      |                       |
     |                         | find user by email ----------------->|                       |
     |                         |                                      |                       |
     |                         |-- no user ----------------------------------------------+   |
     |                         |                                      |                   |   |
     |                         |-- user found:                        |                   |   |
     |                         |   BEGIN; SELECT user FOR UPDATE ---->| (serialises       |   |
     |                         |   count rows, last 1h                | concurrent        |   |
     |                         |                                      |  requests)        |   |
     |                         |   count >= 3 ? --yes--> ROLLBACK ---------------------+  |   |
     |                         |        |no                           |                   |   |
     |                         |   raw = 32 random bytes              |                   |   |
     |                         |   UPDATE tokens SET dead_at=now()    |                   |   |
     |                         |     WHERE user_id=? AND dead_at NULL>|  (kills old link) |   |
     |                         |   INSERT (sha256(raw), user_id,      |                   |   |
     |                         |     now, now+30m) ------------------>|                   |   |
     |                         |   COMMIT                             |                   |   |
     |                         |   enqueue job {to, raw link} ------------------------------>|--> mail provider
     |                         |        |                             |                   |   |    (3 retries,
     |<-- 200 same generic message <----+-------<----------------------+-------<-----------+   |     then drop)
     |   "If an account exists for that address, we've sent a link."   (identical in all cases)

 Paths that send nothing:  unknown address | over 3/hour (no row, no job, old link untouched)

==================== 2. LINK-CLICK FLOW ====================

 GET /reset?token=RAW                                  (page load)
     |-> API: h = sha256(RAW); SELECT WHERE token_hash=h AND dead_at IS NULL AND expires_at>now()
     |        found      --> render "choose a new password" form (RAW kept in the form)
     |        not found  --> render "this link has expired, request a new one" page
     |                       (unknown, expired, used and superseded all look the same)

 POST /reset {token: RAW, password}                    (form submit)
     |-> 1. validate password: len >= 12 AND not in breached list
     |        fail --> re-show form with reason. Nothing is written; link stays live; retry until expiry.
     |-> 2. BEGIN
     |        UPDATE tokens SET dead_at=now()
     |          WHERE token_hash=sha256(RAW) AND dead_at IS NULL AND expires_at>now()
     |          RETURNING user_id                         (this is the second token check, atomic)
     |        0 rows --> ROLLBACK --> "this link has expired, request a new one" page
     |        1 row  --> UPDATE users SET password_hash=hash(password) WHERE id=user_id
     |                   DELETE FROM sessions WHERE user_id=user_id     (every device, incl. this one)
     |                   COMMIT
     |-> 3. enqueue "your password was changed" email to the account address
     |-> 4. 302 redirect to /login   (no session created; user logs in manually)

==================== 3. FAILURE PATHS ====================

 Failure                                   Result
 ----------------------------------------  -------------------------------------------------------
 Unknown email                             Generic message; no row, no email
 Over 3 links in rolling hour              Generic message; no row, no email, existing link kept
 Enqueue fails after COMMIT                Log; generic message anyway; user may request again
 Mail send fails 3x (worker drops job)     Link exists but never arrives; user gets no signal
                                           -> user re-requests (counts toward the 3/hour)
 Link expired / used / superseded          Expired page at load and at submit
 Two submits race on one link              Conditional UPDATE: one wins, other gets expired page
 Password too short or breached            Form re-shown; link stays usable
 Breached-list lookup unavailable          Treat as rejected ("try again"); never accept unchecked
 DB error in step 2                        Whole transaction rolls back: password, link and
                                           sessions all unchanged; show generic error, link live
 "Password changed" email dropped          Reset still stands; user just gets no notice
~~~

Notes

- **Storage.** One table. The raw token lives only in the link and, briefly, in the queued job. Only `sha256(raw)` is stored. Rows are kept after use so the same table gives the rate-limit count. Purge old rows with a periodic delete.
- **Rate limit and "kill earlier link".** Both run in one transaction that holds a row lock on the user. This stops parallel requests from slipping past the limit of 3 or leaving two live links.
- **Check on submit.** The burn is a single conditional UPDATE, so the second token check and the "works once" rule are the same atomic statement. The password is validated before it, so a rejected password never burns the link.
- **Logout.** Deleting the user's `sessions` rows in the same transaction as the password change is enough, because the API checks `sessions` on every request.
- **Silent mail loss.** The existing worker drops failed jobs without telling anyone. A dropped reset email still uses up one of the 3 hourly sends and replaces the previous link. The user can request again, but the client can't see the failure. I'm not changing the worker, as the brief says to keep scope small. A failure alert on the worker is a sensible follow-up.
- **Enumeration.** Responses are identical, and the send is queued rather than done inline, so known and unknown addresses take similar time. The extra DB work for known accounts is small.
- **Link hygiene.** Send the reset page with `Referrer-Policy: no-referrer` and don't log the query string, so the raw token doesn't leak.