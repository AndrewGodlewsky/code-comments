# Password reset by emailed link: design

```
A. REQUEST FLOW   POST /forgot-password {email}

Client                API server                    Postgres                 Email queue -> worker -> mail provider
  |  email               |                              |                              |
  |--------------------->|  normalise email             |                              |
  |                      |  SELECT user by email ------>|                              |
  |                      |<-----------------------------|                              |
  |                      |                              |                              |
  |                      |  user not found?--YES--------+--------> (nothing stored, nothing queued)
  |                      |                              |                              |
  |                      |  BEGIN                       |                              |
  |                      |  SELECT users row FOR UPDATE>|  (serialises requests per account)
  |                      |  COUNT password_resets       |
  |                      |   WHERE user_id=? AND        |
  |                      |   created_at > now()-1h ---->|
  |                      |<--- n                        |
  |                      |  n >= 3? --YES--> ROLLBACK --+--> (no link, no email)
  |                      |                              |                              |
  |                      |  NO: token = 32 random bytes |                              |
  |                      |  UPDATE password_resets      |                              |
  |                      |   SET consumed_at=now()      |                              |
  |                      |   WHERE user_id=? AND        |                              |
  |                      |   consumed_at IS NULL ------>|  (kills earlier unused link)
  |                      |  INSERT password_resets      |                              |
  |                      |   (user_id, sha256(token),   |                              |
  |                      |    created_at=now(),         |                              |
  |                      |    expires_at=now()+30min) ->|                              |
  |                      |  COMMIT                      |                              |
  |                      |  enqueue job {to, link(token)}----------------------------->|
  |                      |                              |                              |-- send --> provider
  |                      |                              |                              |   fail: retry x3 w/ backoff
  |                      |                              |                              |   still failing: log, drop
  |  200 "If an account exists for that address, we've sent a link."   <-- identical in ALL branches above
  |<---------------------|

B. LINK-CLICK FLOW   GET /reset-password?token=T   then   POST /reset-password {token, new_password}

Client                API server                         Postgres
  |-- GET ?token=T ----->|  h = sha256(T)
  |                      |  SELECT * FROM password_resets
  |                      |   WHERE token_hash=h ---------->|
  |                      |<--------------------------------|
  |                      |  row missing OR consumed_at set OR expires_at <= now ?
  |<-- "this link has expired, request a new one" page <----YES
  |                      |  NO
  |<-- "choose a new password" form (token kept in the form, not logged) 
  |
  |-- POST {T, pw} ----->|  h = sha256(T)
  |                      |  length(pw) < 12 ? ------------> 422 "too short"      (link stays usable)
  |                      |  pw on breached list? ---------> 422 "choose another" (link stays usable)
  |                      |  BEGIN
  |                      |  SELECT reset row WHERE token_hash=h FOR UPDATE -->|
  |                      |  missing / consumed / expired? -> ROLLBACK -> "expired" page
  |                      |  UPDATE users SET password_hash=hash(pw) --------->|
  |                      |  UPDATE password_resets SET consumed_at=now() ---->|
  |                      |  DELETE FROM sessions WHERE user_id=? ----------->|  (every device, incl. this one)
  |                      |  COMMIT
  |                      |  enqueue "your password was changed" email ------> email queue -> worker (as in A)
  |<-- 302 /login <------|  (no session created, no auto-login)

C. FAILURE PATHS

  Unknown email ............ same 200 message, no row, no job
  Over 3/hour .............. same 200 message, no row, no job
  Enqueue fails after COMMIT  row exists, no email; generic 200 still returned; error logged;
                           user can re-request (this counts toward the 3/hour)
  Mail send fails 3x ....... job dropped, logged, nobody told; link stays valid until expiry/replacement;
                           user can re-request
  Link expired/used/replaced  GET and POST both show the "expired, request a new one" page
  Weak/breached password ... 422 with reason, token untouched, retry allowed until expiry
  Breached-list check down . fail closed: reject with "try again shortly", token untouched
  Double submit / two tabs . row lock: first commit wins; second sees consumed_at and gets the expired page
  Changed-password email fails  reset still stands (it is sent after COMMIT); logged and dropped as above
```

## Notes

**Data model.** One new table, `password_resets(id, user_id, token_hash UNIQUE, created_at, expires_at, consumed_at NULL)`. No other schema changes.
- The raw token is never stored.
- A row counts as live while `consumed_at IS NULL AND expires_at > now()`.
- `consumed_at` covers both "used" and "replaced by a newer link". The two cases need no separate handling.
- Index `(user_id, created_at)` for the rate-limit count.

**Rate limit.** The limit is the number of `password_resets` rows for the account created in the last hour, so no separate counter is needed.
- The `FOR UPDATE` lock on the user row makes count, invalidate and insert atomic. Parallel requests cannot exceed 3.
- Rows are kept after expiry or use, because the count depends on them. Prune rows older than about a day with a periodic job.
- Emails that fail to send still count toward the limit. This is acceptable and errs toward safety.

**Same response everywhere.** The endpoint always returns the same message. Unknown-address requests also skip the lock, insert and enqueue, so response time differs slightly from the known-address path. If that timing difference matters, add a small fixed delay or do the known-address work after responding.

**Token handling.** The token appears only in the emailed link. One unavoidable exception is the queue job payload, because the worker needs the link to send it.
- Keep that payload out of logs. The worker's failure log should record the `password_resets.id`, never the job body.
- The job is dropped after the final failure, so the token is not retained.
- Set `Referrer-Policy: no-referrer` and `Cache-Control: no-store` on the reset page. This keeps the token out of Referer headers and caches.

**Two checks of the token.** The GET check is only for user experience. The POST check inside the transaction, under `FOR UPDATE`, is the real enforcement. It guarantees the link works once even with concurrent submits.

**Sessions.** The API checks `sessions` on every request, so deleting all of the user's session rows logs out every device immediately. This is in the same transaction as the password change, so the password and the sessions can never get out of step.

**Silent email failure.** The existing worker drops failed jobs without telling anyone, and this design does not change that.
- The user sees the generic message either way and may wait for an email that never comes.
- The recovery is to request again, within the 3/hour limit.
- If this matters, a follow-up could add a failure hook or metric to the worker. It is out of scope here.

**Order of work on success.** Everything that must be consistent (password, token burn, session wipe) is in one transaction. The "password changed" email is enqueued only after COMMIT, so a queue problem never rolls back a successful reset.
