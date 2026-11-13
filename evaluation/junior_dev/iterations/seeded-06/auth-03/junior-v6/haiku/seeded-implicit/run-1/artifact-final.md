# Password reset by emailed link

A user who cannot log in enters their email address on "Forgot password?". If an account exists for that address, the server creates a one-time link that works for 30 minutes and emails it. The user opens the link, chooses a new password, and goes to the login page. They are not logged in.

The flow has three parts because each one runs at a different time: the request, opening the link, and saving the password. Each part checks the token again, so an old or used link never works.

Today the web client calls the API server, which reads and writes Postgres. The API does not send mail itself. It adds a job to the Email queue. The Email worker takes the job and sends it through the Mail provider. If a send fails, the worker retries up to 3 times with backoff, then logs the failure and drops the job. Nobody is told.

## Terms

- **Account**: a row in `users`. It holds the password hash.
- **Session**: a row in `sessions`. There is one for each logged-in device. The API checks it on every request.
- **Raw token**: 32 random bytes. It goes only into the reset link, and into the mail job until the worker sends it.
- **Token hash**: the SHA-256 hash of the raw token. It is the only form of the token that the database stores.
- **reset_tokens**: a table with one row for each link issued. Each row holds the account, the token hash, the issue time, the expiry time (issue time plus 30 minutes) and the used time.
- **Used time**: a value on a reset_tokens row. It stays empty until the password is saved. Once it is set, the link never works again.
- **Dead link**: a link whose row is missing, whose expiry time has passed, or whose used time is set.
- **Rolling hour**: the 60 minutes before now.
- **Transaction**: a group of database changes that all commit together or all roll back.
- **Row lock**: a lock on one `users` row. Another request for the same account waits until the first transaction ends.
- **Conditional update**: an update that changes a row only if the row still passes a test. Here the test is "unused and unexpired". If no row passes, nothing changes.
- **Email queue**: where the API adds a mail job. The Email worker takes jobs from it.
- **Email worker**: the process that takes mail jobs from the queue and sends them through the Mail provider.
- **Mail provider**: the third-party service that delivers the email.
- **Generic message**: "If an account exists for that address, we've sent a link." Every request case shows this same text.
- **Breached-password list**: a list of passwords known to have leaked. The brief does not say where it comes from.

## Diagram

```
 Browser ---> API server ---> Postgres
                 |            (users, sessions, reset_tokens)
                 |
                 +---> Email queue ---> Email worker ---> Mail provider

 A. REQUEST                          (POST: email address)

  look up account by email
        | no account ------------------------> respond: generic message
        | found
        v
  BEGIN transaction
     lock the account's users row          (a second request waits here)
     count reset_tokens rows for this account, created in the rolling hour
        | 3 or more -----> end, no change --> respond: generic message
        | fewer than 3
        v
     set used time on the account's unused reset_tokens rows   (kills old links)
     insert reset_tokens row: account, token hash, expires = now + 30 min
     add "reset link" job to Email queue       (same transaction only if queue is in Postgres)
        | any step fails --> ROLLBACK ---------> respond: generic message
        | all done
     COMMIT
        v
  respond: generic message
        .
        . later, Email worker sends the job; retries up to 3 times

 B. OPEN LINK                        (GET: token from the link)

  hash the token from the link, find reset_tokens row by hash
        | no row, expired, or used time is set --> page: "this link has expired, request a new one"
        | valid
        v
  show "choose a new password" form, with the raw token in a hidden field
                                       (no row is changed)

 C. SET PASSWORD                     (POST: hidden token, new password)

  hash the token, find reset_tokens row by hash
        | no row, expired, or used time is set --> page: "this link has expired, request a new one"
        | valid
        v
  check new password: 12+ characters, not on breached-password list
        | rejected ------------------------> show the reason on the form (token not changed)
        | accepted
        v
  BEGIN transaction
     conditional update: set used time on the token row,
                         only if it is still unused and unexpired
        | no row updated ------------------> ROLLBACK -> expired page
        | one row updated
        v
     update users password hash
     delete every sessions row for this account (all devices)
     add "password changed" job to Email queue
  COMMIT
        v
  redirect to login page (no login)
```

Notes:
- The link carries the raw token, URL-safe encoded, so it needs no escaping.
- Step A locks the account's row before it counts. Two requests for one account therefore cannot both see a count of 2.
- Step C puts the raw token in a hidden form field. No extra cookie or session is needed.
- Opening a link never sets used time. Saving the password does.

## Steps in order

1. **Request (A).** Starts when someone posts an email address on the Forgot password form.
   - Look up the account by email. If there is none, show the generic message and stop. Nothing is created or sent.
   - If the account exists, open a transaction and lock its `users` row. A second request for the same account waits here.
   - Count the account's reset_tokens rows created in the rolling hour. The limit is per account, not per IP address, because the brief sets it on an account. If the count is 3 or more, end the transaction with no change and show the generic message. No row is created and no email is sent.
   - If the count is under 3, set used time on the account's unused reset_tokens rows. This kills any earlier link. Insert a new reset_tokens row with the account, the token hash, and an expiry of now plus 30 minutes. Add a "reset link" job to the Email queue. Commit.
   - Show the generic message.
   - The database keeps only the token hash. Rows are never deleted, because the rate-limit count needs them.
   - If any step before the commit fails, the transaction rolls back. Show the generic message.
2. **Send the email (worker).** Starts when the job reaches the Email worker. The worker builds the link from the raw token and sends it through the Mail provider. If the send fails, it retries up to 3 times with backoff. Then it logs the failure and drops the job. The job holds the raw token until it is sent or dropped.
3. **Open the link (B).** Starts when the user clicks the link (a GET request). The server hashes the token from the URL and finds the reset_tokens row by hash. The hash column is indexed. If the row is missing, expired or used, show the page "this link has expired, request a new one". If the link is valid, show the "choose a new password" form with the raw token in a hidden field. This step changes nothing.
4. **Set the password (C).** Starts when the form is posted with the hidden token and the new password.
   - Hash the token and find the row again, using the same rules as step 3. If the link is dead, show the expired page.
   - Check the new password. It must be at least 12 characters and must not be on the breached-password list. If it fails, show the reason on the form. The token is not changed, and the user can try again until the link expires.
   - If the password passes, open a transaction. Run a conditional update that sets used time on the row, only if the row is still unused and unexpired. If no row changed, roll back and show the expired page. This also means only one of two submits of the same link can succeed.
   - Store the new password hash on the `users` row. Delete every `sessions` row for the account, including the device that did the reset. Add a "password changed" job to the Email queue. Commit. The four changes commit together or not at all.
   - Redirect to the login page. Do not start a session. The user is not logged in.
5. **Send the confirmation (worker).** The same retry rule as step 2 applies. If the send fails, the user is not told. The password has already changed.
6. **A device that was logged in (any later request).** Its session row is gone. The API checks sessions on every request, finds no row, and refuses the request as not logged in. The brief does not set the response or page for this, so it is not decided here. The user logs in again with the new password.

## Rules across the steps

- **Only the hash is stored.** A leaked database does not expose live links.
- **Finding the row.** The server hashes the token it receives and looks up the row by that hash.
- **Killing old links.** A new link burns the account's other unused rows. It does not delete them.
- **Rate limit.** At most 3 reset emails per account in any rolling hour. A request over the limit creates no row, sends no email, and still gets the generic message.
- **Two emails.** A new link kills the older one. If the older email arrives late, its link shows the expired page. The design does not tell the user which email to use.
- **Concurrent submits.** The conditional update lets only one submit of a link succeed. The other rolls back and sees the expired page.
- **One save.** Burning the link, changing the password, deleting the sessions and queuing the email are one transaction. Either all four happen or none do.

## What happens when things fail

| Where | What goes wrong | What happens | What the user sees |
|---|---|---|---|
| A | No account for the address | Nothing created, nothing sent | Generic message |
| A | 3 or more links in the rolling hour | Nothing created, nothing sent | Generic message |
| A | Insert, burn-old or queue add fails, queue in Postgres | Transaction rolls back; old links stay as they were; error logged | Generic message; no new link exists |
| A | Queue add fails, queue outside Postgres | Old links are already burned and the new link row is committed, but no email is queued; error logged | Generic message; the new link never arrives (see open questions) |
| Worker | Mail send fails | Retries up to 3 times with backoff; then logs and drops the job | Nothing; the user can ask again, which counts against the limit |
| B | Link missing, expired or used | Nothing changes | "This link has expired, request a new one" |
| B or C | Old link opened after a newer one was issued | Old link is burned; nothing changes | Expired page; the user is not told which email works |
| C | Link missing, expired or used at submit | Nothing changes | Same expired page |
| C | Password under 12 characters, or on the breached list | Nothing changes; token stays usable until expiry | Reason shown on the form; user can try again |
| C | Save fails at any step (queue in Postgres) | Whole transaction rolls back: password, token and sessions unchanged; no email | Error; link still works if it has not expired |
| C | Two submits of one link at once | Only one conditional update succeeds; the other rolls back | Expired page for the second |
| Worker | Confirmation email fails | Retries up to 3 times; then logs and drops the job | Login page; the password has already changed and the user is not told |

## Open questions

- Where does the Email queue run: in Postgres or in another service? The rollbacks above assume it is in Postgres. If it is not, the mail job cannot share the transaction. A failed job add then leaves a link with no email, or a changed password with no confirmation, and the old links are already burned.
- The raw token sits in the mail job until the job is sent or dropped. The brief says the raw token is never stored, and the queue holds it. Does that count as storing it? How long are failed jobs kept? A decision is needed.
- Should there also be an IP-address limit? The brief sets only a per-account limit.
- A user whose reset email is dropped after retries has no way to learn of it. They can ask again, which counts against the limit.
- A user who receives two reset emails is not told which one works.
- A user whose confirmation email is dropped is not told that the password changed.
- How long are old `reset_tokens` rows kept? They must stay at least one hour for the rate limit. The cleanup rule is not set.
- Where does the breached-password list come from, and how is it updated? The brief does not say.