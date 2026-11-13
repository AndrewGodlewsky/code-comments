Password reset by emailed link

A user who cannot log in enters their email and gets a one-time link. The link opens a page where they choose a new password. Today the browser talks to the API server, Postgres holds users and sessions, and mail goes through an existing email queue to an email worker and the mail provider. This design adds one table and three flows: request a link, open the link, set the password.

Terms
- Reset token: 32 random bytes. It appears only inside the emailed link.
- reset_tokens: new Postgres table, one row per link: user id, SHA-256 hash of the token, issued time, expiry (issued + 30 minutes), used flag. The raw token is never stored. Rows are never deleted, so they also give the count for the hourly limit.
- Live link: a row that is unused and not expired.
- Session: a row in the sessions table for one logged-in device. The API checks it on every request. Deleting a user's session rows logs out every device, including the one doing the reset.

```
 Browser ---> API server ---> Postgres
                  |           (users, sessions, reset_tokens)
                  |
                  +---> Email queue ---> Email worker ---> Mail provider

 1. Forgot password (submit email)
    look up user by email
      not found ---------------------> stop: generic message, nothing sent
    count this account's reset_tokens rows created in the last hour
      3 or more ---------------------> stop: generic message, nothing sent
    one transaction: mark the account's live links used, insert new row (hash only)
    put "send reset email" job on the Email queue (contains the link)
      queue fails -------------------> log it; the row stays; still show generic message
    respond at once: generic message (does not wait for the send)

 2. Open link (token from the URL)
    hash token, find row
      missing / expired / used ------> "this link has expired, request a new one" page
    live ----------------------------> show new-password form
                                       (form keeps the token in a hidden field)

 3. Set password (token from hidden field + new password)
    hash token, find row; if not live -> same "expired" page
    password under 12 chars or on breached list -> show error, link stays live
    one transaction:
      mark link used: update where id = row and used = false and expiry > now
        0 rows updated (second submit won) -> roll back, show "expired" page
      save new password hash, delete all of the user's sessions
      any failure -> nothing changed, show error, link stays live
    put "password changed" email job on the queue
      queue fails -------------------> log it; password stays changed; no retry
    redirect to login page (no automatic login)
```

Notes
- The generic message is always: "If an account exists for that address, we've sent a link."
- The rate limit is per account, not per IP: at most 3 reset emails in a rolling hour. Links killed by a newer request still count, because their rows remain.
- A link is marked used only when the password is saved, so a rejected password can be retried until the link expires.
- Step 3 checks the token again because it may have expired or been used since step 2. The conditional update makes a double submit safe: the second one changes no rows and loses.
- The "password changed" email goes to the account's email address.
- If an email is never delivered (queue failure, or the worker gives up after its 3 retries with backoff, then logs and drops the job), nobody is told. The user can request a new link, within the hourly limit.
- The new password is hashed the same way as login passwords today.
- If the breached-password check is unavailable, reject the password with "try again later" and keep the link live.

Open questions
- Is the breached-password list a local file or an external service? The failure handling above assumes it can fail.
- Which hash algorithm do login passwords use? The reset must reuse it.