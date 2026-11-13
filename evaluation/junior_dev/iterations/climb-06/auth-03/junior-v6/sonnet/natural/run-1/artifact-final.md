# Password reset by emailed link: design

A user who cannot log in enters their email address under "Forgot password?" and gets a one-time link that opens a page for choosing a new password. Today the web client talks to the API server. Postgres holds `users` (with the password hash) and `sessions`. Outgoing mail goes through an existing email queue. The flow has two halves. In the request flow, the API checks a per-account limit, stores only a hash of a random token, and queues an email containing the link. In the link-click flow, the API checks the token again, saves the new password, burns the token and logs the user out everywhere in one database transaction. The request endpoint always gives the same answer, so nobody can learn which addresses have accounts.

## Terms

- **Token**: 32 random bytes. It appears only inside the emailed link. We store only its SHA-256 hash. Between generation and the queue job it lives only in the API server's memory.
- **Reset row**: a row in the new table `password_resets`. One row is one issued link.
- **Live link**: a reset row with `consumed_at IS NULL AND expires_at > now()`. A link is valid 30 minutes after it is issued and works once.
- **Link**: `https://<client base URL>/reset-password?token=T`. The API builds it from a configured client base URL. It points at the page served by the web client, not at the API. The page then calls the API to check and to submit.
- **Normalise email**: trim spaces and lowercase the address before the lookup, so "Bob@X.com " finds "bob@x.com".
- **sessions table**: one row per logged-in device. The API looks up the caller's session row on every request. If the row is gone, the request is rejected, so that device is logged out at once.
- **Email queue, worker, mail provider**: existing. The API adds a job to the queue (it does not wait for the send). The email worker takes the job and sends it through our third-party mail provider. If a send fails, the worker retries up to 3 times with backoff, then logs the failure and drops the job. Nobody is notified.
- **Queue job**: `{to, link}`. The raw token is inside the link.
- **`FOR UPDATE`**: a Postgres row lock. Other transactions that lock the same row wait until this one commits or rolls back.
- **hash(pw)**: the same password hashing login uses to verify passwords. See Open questions.
- **Breached-password list**: known leaked passwords that a new password must not match. See Open questions.

## Diagram

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
  |                      |  n >= 3? --YES--> ROLLBACK --+--> (no link, no email, older link untouched)
  |                      |                              |                              |
  |                      |  NO: token = 32 random bytes (kept in memory only)           |
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
  |<---------------------|   (sent after the enqueue call returns; never waits for the mail send)

B. LINK-CLICK FLOW   client page /reset-password?token=T  (check on load)  then  POST /reset-password {token, new_password}

Client (serves the page)   API server                       Postgres
  |-- page loads, reads T -|                                  |
  |-- check (T) ---------->|  h = sha256(T)
  |                        |  SELECT * FROM password_resets
  |                        |   WHERE token_hash=h ---------->|
  |                        |<--------------------------------|
  |                        |  row missing OR consumed_at set OR expires_at <= now ?
  |<-- "invalid" <---------|----YES
  |   client shows the "this link has expired, request a new one" page
  |<-- "valid" <-----------|  NO
  |   client shows the "choose a new password" form (token kept in the page, not logged)
  |
  |-- POST {T, pw} ------->|  h = sha256(T)
  |                        |  length(pw) < 12 ? ------------> 422 "too short"      (link stays usable)
  |                        |  pw on breached list? ---------> 422 "choose another" (link stays usable)
  |                        |  BEGIN
  |                        |  SELECT reset row WHERE token_hash=h FOR UPDATE -->|
  |                        |  missing / consumed / expired? -> ROLLBACK -> "expired" page
  |                        |  UPDATE users SET password_hash=hash(pw) --------->|
  |                        |  UPDATE password_resets SET consumed_at=now() ---->|
  |                        |  DELETE FROM sessions WHERE user_id=? ----------->|  (every device, incl. this one)
  |                        |  COMMIT
  |                        |  enqueue "your password was changed" email ------> email queue -> worker (as in A)
  |<-- 302 /login <--------|  (no session created, no auto-login)

C. FAILURE PATHS

  Unknown email ............ same 200 message, no row, no job
  Over 3/hour .............. same 200 message, no row, no job, earlier live link stays live
  Enqueue fails after COMMIT  row exists, no email; the earlier link is already killed, so the user has
                           no working link; generic 200 still returned; error logged;
                           user can re-request (this counts toward the 3/hour)
  Mail send fails 3x ....... job dropped, logged, nobody told; link stays valid until expiry/replacement;
                           user can re-request
  Link expired/used/replaced  check and POST both lead to the "expired, request a new one" page
  Weak/breached password ... 422 with reason, token untouched, retry allowed until expiry
  Breached-list check down . fail closed: reject with "try again shortly", token untouched
  Double submit / two tabs . row lock: first commit wins; second sees consumed_at and gets the expired page
  Changed-password email fails  reset still stands (it is sent after COMMIT); logged and dropped as above
```

## Notes

**Data model.** One new table, `password_resets(id, user_id, token_hash UNIQUE, created_at, expires_at, consumed_at NULL)`. No other schema changes. The raw token is never stored. `consumed_at` covers both "used" and "replaced by a newer link", so the two need no separate handling. Clicking a replaced link shows the same "expired, request a new one" page. Index `(user_id, created_at)` serves the rate-limit count.

**Rate limit.** An account can be sent at most 3 reset emails in any rolling hour. The limit is the count of `password_resets` rows for the account created in the last hour, so no separate counter is needed.
- The `FOR UPDATE` lock on the user row makes count, invalidate and insert atomic, so parallel requests cannot exceed 3.
- A request over the limit gets the same generic message, creates no link and sends no email. It rolls back, so it does not kill the older live link.
- A blocked user can get a new link once the oldest of the 3 rows is over an hour old, so the wait is at most an hour. A link lives only 30 minutes, so a user whose emails never arrived may wait up to about 30 minutes after the last link expired.
- Rows are kept after expiry or use, because the count depends on them. A periodic job prunes rows older than about a day.
- Emails that fail to send still count toward the limit. This errs toward safety.

**Same response everywhere.** The endpoint always returns "If an account exists for that address, we've sent a link." Unknown addresses get it too, and nothing is sent to them. It is returned after the enqueue call returns. Unknown-address requests skip the lock, insert and enqueue, so their response time differs slightly. If that matters, add a small fixed delay or do the known-address work after responding.

**Token handling.** The token appears only in the emailed link. The one unavoidable exception is the queue job payload, because the worker needs the link to send it.
- Keep that payload out of logs. The worker's failure log records the `password_resets.id`, never the job body.
- The job is dropped after the final failure, so the token is not retained.
- Set `Referrer-Policy: no-referrer` and `Cache-Control: no-store` on the reset page (served by the web client), to keep the token out of Referer headers and caches.

**Two checks of the token.** The check on page load is only for user experience: the user learns a link is dead before typing a password. The page asks the API, and the API answers valid or invalid. The POST check inside the transaction, under `FOR UPDATE`, is the real enforcement. It makes the link work once even with concurrent submits. The page carries the token back in the POST body.

**Password rules.** A new password must be at least 12 characters and must not be on the breached-password list. A rejected password leaves the link usable until it expires. These checks run before the transaction, to keep it short. So if the link is dead and the password is also bad, the user sees the 422 first and the expired page on the next try. This is harmless.

**Sessions and login after reset.** Deleting all of the user's session rows logs out every device immediately, including the one that did the reset. It is in the same transaction as the password change, so the two cannot get out of step. The user is redirected to `/login` and logs in with the new password. They are not logged in automatically. Anyone who controls the mailbox can reset the password; that is inherent to email reset. The 30-minute single-use link, the logout of all devices and the "your password was changed" email are the defences.

**Order of work on success.** Password, token burn and session wipe are in one transaction. The "password changed" email is enqueued only after COMMIT, so a queue problem never rolls back a successful reset.

**Silent email failure.** The existing worker drops failed jobs without telling anyone, and this design does not change that. The user sees the generic message either way and may wait for an email that never comes. The recovery is to request again, within the 3/hour limit. A follow-up could add a failure hook or metric to the worker. It is out of scope here.

## Open questions

- Where does the breached-password list live, and is it a local file or an external service? The design needs only a yes/no answer and fails closed if the check is down.
- Is `users.email` already stored lowercase and trimmed? If not, the lookup must compare case-insensitively.
- The email worker's exact retry delays are unknown. The design relies only on "up to 3 retries, then drop".
- Which password hashing algorithm does login use? The reset must use the same one.
- What is the exact URL of the API's token-check endpoint? The design needs only "page asks API, API answers valid or invalid".
