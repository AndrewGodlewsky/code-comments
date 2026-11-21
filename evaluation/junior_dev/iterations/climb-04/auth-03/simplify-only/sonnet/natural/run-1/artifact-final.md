PASSWORD RESET BY EMAILED LINK

```
SUMMARY
  Today: users log in with a password. The API checks the sessions table on every
  request. Mail goes through an email queue: the API adds a job, a worker sends it
  through the mail provider.
  New: a user who forgot their password asks for a link by email. The link opens a
  page where they choose a new password. A successful reset logs them out everywhere.

TERMS
  reset link ..... URL holding a one-time token (32 random bytes). Valid 30 minutes.
  token hash ..... SHA-256 of the token. Only the hash is stored, never the token.
  password_resets  the one new table:
                   (id, user_id FK, token_hash UNIQUE, created_at, expires_at, used_at NULL)
  live link ...... a row with used_at NULL and expires_at in the future.
  Existing tables: users (has the password hash), sessions (one row per logged-in device).

=====================================================================
A. REQUEST FLOW   POST /forgot-password {email}
=====================================================================

 Browser                API server                    Postgres            Email queue -> Worker -> Provider
   |  email               |                              |                        |
   |--------------------->|                              |                        |
   |                      | normalize email, look up user|                        |
   |                      |----------------------------->|                        |
   |                      |<-----------------------------|                        |
   |                      |                                                       |
   |                      +-- no such user ---------------------------------+     |
   |                      |                                                 |     |
   |                      +-- user found:                                   |     |
   |                      |     BEGIN (lock the users row: SELECT FOR UPDATE)|     |
   |                      |     count password_resets WHERE user_id          |     |
   |                      |       AND created_at > now()-1h                  |     |
   |                      |                                                 |     |
   |                      |     count >= 3 ---- ROLLBACK, no link, no mail -+     |
   |                      |                                                 |     |
   |                      |     count < 3:                                  |     |
   |                      |       token = 32 random bytes                   |     |
   |                      |       UPDATE password_resets SET used_at=now()   |     |
   |                      |         WHERE user_id AND used_at IS NULL        |     |
   |                      |         (kills earlier unused links)             |     |
   |                      |       INSERT (sha256(token), expires_at=now()+30m)|    |
   |                      |     COMMIT                                       |     |
   |                      |     enqueue "reset" job {user, raw token link} ---|---->|--> send
   |                      |                                                 |     |
   |<---------------------+<------------------------------------------------+     |
   |  200 "If an account exists for that address, we've sent a link."  (always)    |

 Same body and status on every branch. Do the work off the response path where
 possible, so timing does not reveal whether the account exists.

=====================================================================
B. LINK-CLICK FLOW
=====================================================================

 GET /reset?token=T   (page load)
   |
   v
 find password_resets row where token_hash = sha256(T)
   |
   +-- no row / used_at set / expires_at < now() --> "This link has expired, request a new one" page
   |                                                  (links to Forgot password)
   +-- valid --> render "choose a new password" form (token kept in the page, not logged)

 POST /reset {token T, new password}   (form submit)
   |
   v
 re-check token exactly as above
   +-- invalid/expired/used --> "This link has expired" page
   |
   +-- valid:
        password < 12 chars OR on breached list
          --> re-show form with the error; link NOT burned; retry until it expires
        password ok:
          BEGIN
            claim link: UPDATE password_resets SET used_at=now()
                        WHERE id=? AND used_at IS NULL AND expires_at > now()
                        (0 rows updated => someone else used it => expired page, ROLLBACK)
            UPDATE users SET password_hash = hash(new password)
            DELETE FROM sessions WHERE user_id = ?     (all devices, including this one)
          COMMIT
          enqueue "your password was changed" email
          302 -> /login   (no session is created)
```

Notes

- **Rate limit.** At most 3 resets per account in a rolling hour. The count includes killed and used rows, because each one was an email. Locking the `users` row stops two concurrent requests from both slipping under the limit. Over the limit, the user still sees the generic message.
- **One live link.** A new link marks older unused rows as used in the same transaction, so an account has at most one live link.
- **Single use.** The conditional UPDATE at reset time enforces it. The page-load check is only for user experience.
- **Reset and logout.** Password change, link burn and session deletion share one transaction, so a failure leaves the account unchanged. Deleting the `sessions` rows logs out every device, because the API checks that table on every request. No session is created afterwards.
- **Raw token in the queue.** The job carries the raw token to build the link. Remove the job after sending or failing, and never log job payloads, including the worker's failure log.
- **Cleanup (optional).** A periodic job may delete `password_resets` rows more than 1 hour past expiry. Do not delete newer rows, since the rate limit counts them.

Failure paths

| Step | What goes wrong | What happens |
|---|---|---|
| Request | Unknown email | Generic message. Nothing stored or sent. |
| Request | Over 3 in a rolling hour | Generic message. No row, no mail. |
| Request | Database error | Transaction rolls back. Log it. Return the same generic message. |
| Request | Enqueue fails after COMMIT | Log it. The user can request again. This counts toward the 3 per hour. |
| Request | Worker fails to send | Worker retries 3 times with backoff, then logs and drops the job. The user is not told (existing behavior, see open questions). |
| Click or submit | Token invalid, expired or used | Show the "this link has expired" page, on load and on submit. |
| Submit | Two submits race | The conditional UPDATE lets only one win. The other sees the expired page. |
| Submit | Password too short or breached | Form error. The link stays valid until it expires. |
| Submit | Database error | Whole transaction rolls back. Show "something went wrong, try again". The link stays usable. |
| After reset | Change-notice email fails | The password is already changed. The notice is lost after retries. |

Open questions

- The worker drops a job after 3 failed retries and tells nobody. The user then gets the generic message and no email, and can only request again, up to the hourly cap. For the "password was changed" email, a hijack victim might not be warned. Not changed here because it is outside this feature. Flag it to the worker's owners. A failure alert or a "didn't get it?" hint on the confirmation page is worth considering.