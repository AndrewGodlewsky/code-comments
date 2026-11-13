Password reset by emailed link. A user who cannot log in enters their email and gets a one-time link. The link opens a page where they choose a new password, and a successful reset logs them out everywhere and sends them to the login page. Today the API server adds email jobs to a queue, and a worker sends them through a third-party mail provider; this design reuses that path and adds one table.

```
 Terms
   reset_tokens  New Postgres table, one row per issued link (and so per reset email).
                 Columns: user_id, token_hash, created_at, expires_at, used_at.
   token         32 random bytes. It appears only in the emailed link.
                 We store only its SHA-256 hash, never the raw token.
   session       A row in sessions, one per logged-in device. The API checks it on every request.
   email queue   Existing queue. The API adds a job and moves on; a worker sends it later.
   "live" link   Row exists, used_at is empty, expires_at is in the future.
   "dead" link   Expired, already used, or replaced by a newer link.

 Components
   Browser ---> API server ---> Postgres (users, sessions, reset_tokens)
                    |
                    +--(adds job)--> Email queue --> Email worker --> Mail provider

 Rules that apply to several steps
   - Token: 32 random bytes, stored only as SHA-256 hash.
   - A link is valid 30 minutes after it is issued and works once.
   - A new link kills every earlier unused link for that account.
   - The forgot-password response is always the same generic message.
   - Rate limit: at most 3 reset emails per account in any rolling hour.
   - New password: at least 12 characters and not on the breached-password list.
   - The site URL for links comes from server configuration, never from the
     request's Host header, so a forged request cannot point a link at another site.

 1. Forgot password   (starts: user submits their email; the API responds at once
                       and does not wait for the email to be sent)
   look up user by email (assumed case-insensitive)
     no account : do nothing more (nothing stored, nothing sent)
     account    : count this user's reset_tokens rows created in the last hour
                    3 or more : do nothing more (no token, no email)
                    under 3   : in ONE transaction: mark the user's unused older
                                tokens as used, then insert a new row
                                (token hash, expires_at = now + 30 min)
                                after commit: add job "send reset link" to the queue
                                (recipient + finished link = site URL + raw token;
                                 the API builds the link, the worker only sends it)
                                if adding the job fails: log it, carry on
   ALWAYS respond: "If an account exists for that address, we've sent a link."

 2. Open link        (starts: user clicks the link)
   hash the token from the link, find the row
     live            : show "choose a new password" form
                       (token stays in the page URL; the form sends the same
                        raw token back in a hidden field, so no cookie is needed)
     dead / no row   : show "this link has expired, request a new one"

 3. Submit new password   (starts: user submits the form; token is checked again
                           because the link can die between opening and submitting)
   hash the token, find the row
     dead / no row   : show the same "expired" page
   check the password
     rejected        : show the reason on the form; the link stays live;
                       user may retry until it expires
   accepted: in ONE transaction
       a. save the new password hash in users
       b. set used_at on the token
       c. delete every sessions row for this user (all devices, including this one)
     transaction fails : nothing changes; user sees a generic error and can
                         submit again while the link lives
   after commit: add job "password changed" email to the queue
                 (if adding fails: log it; the reset still stands and the user
                  only misses the notice)
   redirect to the login page (no automatic login)
```

Failures
- Step 1, queue unavailable after commit: the user still sees the generic message (it must never vary). The row still counts toward the 3-per-hour limit. The user can request another link, within the limit.
- Email send fails: the worker retries up to 3 times with backoff, then logs the failure and drops the job. Nobody is notified. A user who never gets the email can request another link, within the limit.
- Step 3, transaction fails: described in the step; the confirmation email is never queued.
- Over the rate limit or unknown address: the user sees the generic message and nothing is sent. Unknown addresses have no account, so they are never counted.

Rollout is not part of this design.

Open questions
- Where the breached-password list lives and how it is checked (local hash list or external service) is not decided.
- Which queue software the email queue uses, and the exact backoff delays, are existing system details not known here.
- Case-insensitive email lookup is assumed, not verified.
- The name of the configuration setting that holds the site URL is not decided.