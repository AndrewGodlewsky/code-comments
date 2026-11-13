```
PASSWORD RESET BY EMAILED LINK

Tables (new: password_resets; existing: users, sessions)
  password_resets(id, user_id FK, token_hash UNIQUE, created_at, expires_at, used_at NULL)
  reset_email_log is not needed: rate limit counts password_resets rows per user_id

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

 Same body, status and (as far as practical) same latency on every branch.

=====================================================================
B. LINK-CLICK FLOW
=====================================================================

 GET /reset?token=T   (page load)
   |
   v
 h = sha256(T); find password_resets row by token_hash
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

=====================================================================
C. FAILURE PATHS
=====================================================================

 Unknown email ............ generic message, nothing stored or sent
 Over 3 in rolling hour ... generic message, no row, no mail
 Invalid/expired/used ..... expired page on load and on submit
 Weak/breached password ... form error, link stays valid
 Two submits race ......... the conditional UPDATE lets only one win
 DB error on request ...... transaction rolls back; return the same generic
                            message (log the error) so nothing leaks
 DB error on reset ........ whole transaction rolls back: password, link
                            and sessions stay as they were; show a
                            generic "something went wrong, try again"
                            (link remains usable)
 Enqueue fails after COMMIT (request) .. log it; user may request again
                            (it counts toward the 3/hour)
 Reset email: worker retries 3x with backoff, then logs and drops
                            (existing behavior, silent to the user)
 Change-notice email fails . password is already changed; the notice is
                            lost after retries (see notes)
```

Notes

- **Storage.** One new table, `password_resets`. We keep the hash only. The raw token exists in the link and in the queued job payload.
- **Rate limit.** The limit counts rows created in the last hour, which includes rows that were killed or used, because each one corresponds to a sent email. Locking the `users` row during check and insert stops two concurrent requests from both slipping under the limit.
- **One live link.** Issuing a new link marks older unused rows as used in the same transaction, so at most one row per account is valid at any time.
- **Expiry and single use.** `expires_at` is set at issue time. Single use is enforced by the conditional UPDATE at reset time, not by the earlier page-load check, which is only for user experience.
- **Reset and logout.** The password change, link burn and session deletion are in one transaction. A failure leaves the account exactly as it was. The deleted `sessions` row is what logs out every device, because the API checks that table on every request.
- **No auto-login.** The redirect goes to /login, and no session is created.
- **Raw token in the queue.** The email job has to carry the raw token to build the link. It is a short-lived secret in the queue, so the job should be removed after sending or failing. Avoid logging job payloads, including in the worker's failure log.
- **Silent email failures (known gap).** The worker drops a job after 3 failed retries and nobody is told. For the reset email, the user sees the generic message, never receives anything, and can only request again (up to the hourly cap). I have not changed the worker, since that is outside this feature. It should be flagged to the owners, and a failure alert or a visible "didn't get it?" retry hint on the confirmation page is worth considering. For the "password was changed" email, a silent failure means a hijack victim might not be warned.
- **Enumeration.** Responses are identical for known, unknown and rate-limited addresses. Do the database work and enqueue off the response path where possible, so timing does not reveal whether an account exists.
- **Cleanup.** An optional periodic job can delete `password_resets` rows older than 1 hour past expiry. Do not delete rows within the last hour, since the rate limit depends on them.
