Password reset by emailed link

Today a user logs in against `users` in Postgres, and each logged-in device has a row in `sessions` that the API checks on every request. Mail already goes through a queue. A user who forgot their password asks for a link by email, opens it, and picks a new password. The link is a one-time secret that we store only as a hash. A successful reset logs the account out everywhere, so anyone who had the old password loses access.

Terms
- Token: 32 random bytes, put only inside the emailed link. We store only its SHA-256 hash, never the raw token.
- reset_tokens: a new Postgres table, one row per issued link: user id, token hash, created time, expiry time (created + 30 minutes), used time (empty until burned).
- Burned: the row's used time is set. A burned link is dead, whether it was used or replaced.
- Email queue / email worker: the API adds a job to the queue. The worker sends it through the third-party mail provider. When a send fails it retries up to 3 times with backoff, then logs the failure and drops the job. Nobody is notified.
- Generic message: "If an account exists for that address, we've sent a link."

```
 Browser ---> API server ---> Postgres
                  |           (users, sessions, reset_tokens)
                  |
                  +---> Email queue ---> Email worker ---> Mail provider

 1. Forgot password (browser submits email)
    look up user
      unknown address ---------------------------> generic message (nothing sent)
    count this user's reset_tokens created in the last hour
      3 or more ---------------------------------> generic message (no token, no email)
    in one transaction: burn the user's unused tokens,
                        insert new row (hash only)
    queue email with the link ---------------------> generic message

 2. Open link (browser loads the new-password page)
    hash the token from the link, find the row
      missing, expired (over 30 min) or burned ----> "this link has expired,
                                                      request a new one" page
      valid -------------------------------------> show the new-password form

 3. Set password (browser submits form)
    in one transaction:
      check the token again (same test as step 2)   invalid -> expired page
      check password: 12+ characters, not on the
        breached-password list                       rejected -> error on the form,
                                                      link stays usable until it expires
      save new password hash
      burn the token
      delete all of the user's sessions (every device, including this one)
    queue "your password was changed" email
    redirect to the login page (no automatic login)
```

Notes
- Step 1 always returns the generic message, for unknown addresses and over-limit requests too, so the response never reveals whether an account exists.
- The rate limit is 3 reset emails per account in any rolling hour. It is counted from reset_tokens rows, so no separate counter exists. Rows are created only when an email is queued, so the count equals emails sent.
- Issuing a new link burns every earlier unused link for that account, in the same transaction as the insert, so only one link works at a time.
- The token is checked at step 2 so the user learns early that the link is dead, and again at step 3 because it may have expired or been used since the page loaded. Burning it in the same transaction as the password change means two submits of the same link cannot both succeed.
- The password is checked before the token is burned, so a rejected password never uses up the link.

What happens when things fail
- Unknown address or over the rate limit: generic message, nothing created or sent.
- Mail send fails: the worker's 3 retries run, then the job is dropped silently. The user sees no error. They can request another link, which counts toward the hourly limit.
- Database error in step 1 or 3: the transaction rolls back, the user sees a generic error page, and nothing is half-saved. The link stays as it was.
- The "password changed" email fails to send: same drop as above. The reset itself still stands.

Open questions
- A dropped reset email is invisible to the user and to us. We have not decided whether to alert on it; the brief keeps the worker's existing behaviour.
- When the user clicks a dead link, we have not decided whether the expired page should say why (expired, used or replaced). The brief shows one message for all three.