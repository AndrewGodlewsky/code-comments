Password reset by emailed link

Today the web client talks to the API server. Postgres holds `users` (with the password hash) and `sessions` (one row per logged-in device; the API checks it on every request). Mail already goes through the Email queue: the API adds a job, and the email worker sends it through the third-party mail provider.

This design adds "Forgot password?". A user who cannot log in enters their email address and gets a one-time link. The link opens a page where they choose a new password. There are three parts: request a link, open the link, set the password. The API only adds jobs to the Email queue and never sends mail itself, so the reply is fast and looks the same whether or not an email is sent.

Terms
- Token: 32 random bytes, the secret in the emailed link. It appears only in the link. We store only its SHA-256 hash, so a database leak cannot be used to reset passwords.
- reset_tokens: a new Postgres table. Each row holds the token hash, the account, the issue time, and whether the token is used or dead.
- Dead token: an unused token replaced by a newer link for the same account. It no longer works.
- Session: a `sessions` row. Deleting it logs that device out, because its next request finds no session and is rejected as not logged in.
- Email queue: the existing queue of mail jobs. The email worker takes jobs from it and sends them.

```
 Browser ---> API server ---> Postgres
                  |           (users, sessions, reset_tokens)
                  |
                  +---> Email queue ---> Email worker ---> Mail provider

 1. Forgot password:  submit email
                   -> look up user by email
                        no account: send nothing, go to "respond"
                   -> rate limit: count ALL reset_tokens rows for this
                        account created in the last hour (live, used and
                        dead); 3 or more: send nothing, go to "respond"
                   -> create token, in one transaction: insert a row with
                        the SHA-256 hash of 32 random bytes, the account
                        and the issue time; mark the account's earlier
                        unused tokens as dead
                   -> after the commit, add an email job (with the raw
                        token in the link) to the Email queue
                   -> respond immediately, without waiting for the send:
                        "If an account exists for that address, we've
                        sent a link."  (the same text on every path)

 2. Open link:        hash the token from the link, find it in reset_tokens
                   -> valid (found, under 30 minutes old, unused, not dead):
                        show the new-password form
                   -> otherwise: show "this link has expired, request a new one"
                   (opening the link changes nothing in the database)

 3. Set password:     validate the token again (same check as above;
                        if invalid, show the same expired page)
                   -> check password: 12+ characters, not on the breached list
                        rejected: show the reason; the token stays valid so
                        the user can retry until it expires
                   -> in one database transaction: mark the token used
                        (only if it is still unused; if no row changes,
                        roll back and show the expired page), save the new
                        password hash in users, delete every sessions row
                        for the account (this includes the session of the
                        person resetting)
                        transaction error: roll back everything, show
                        "something went wrong, try again"; the token is
                        still unused, so the user can resubmit
                   -> after the commit, add a "your password was changed"
                        email job to the queue
                   -> redirect to the login page (no automatic login)
```

Notes
- Links last 30 minutes and work once. The token is marked used only when the new password is saved, not when the link is opened, so a user who opens the link and walks away can open it again until it expires.
- Issuing a new link immediately kills any earlier unused link for that account. This happens in the same transaction as the insert, so two live links never exist at once.
- The forgot-password response is generic, so it never reveals whether an address has an account. Unknown addresses get the same message and nothing is sent to them.
- Rate limit: at most 3 reset emails per account in any rolling hour (per account, not per IP). The count comes from reset_tokens rows of every state, because each row was an email and this stops new links from getting around the limit. No separate counter is needed. Over the limit the user still sees the generic message, but no token is created and nothing is sent.
- Double submit (for example two tabs): the "mark used only if still unused" update lets one submit win. The other changes no row, rolls back and sees the expired page.
- Sessions are deleted in the same transaction as the password save, before the confirmation email is queued, so every old login is already dead when the user is told about the change. A device that was logged out is simply rejected on its next request; what the client then shows is existing behaviour, unchanged here.
- Email worker retries (existing behaviour, unchanged): when a send fails it retries up to 3 times with backoff. After that it logs the failure and drops the job, and nobody is notified. For a reset link, the user requests another link. For the confirmation email, the password is already changed and the email is lost.

What happens when things fail
| Where | Failure | Result |
|---|---|---|
| Create token | API fails before the commit | Nothing changed; the user retries |
| Add email job after commit | API or queue fails | The token exists but no email goes out; the user still saw the generic message and requests again (this counts toward the limit of 3) |
| Send | Mail provider keeps failing | Worker retries 3 times, then drops the job silently |
| Set password transaction | Database error | Everything rolled back, old sessions stay alive; token still usable; user can resubmit |
| Two submits at once | Second finds the token already used | Second rolls back and sees the expired page |
| Confirmation email job | Not added or dropped | Password is already changed; the email is lost |

Open questions
- Where the Email queue lives, what holds it, and whether a job survives the queue or worker being down is part of the existing system and is not known here. A lost reset or confirmation email is accepted, as in the existing system.
