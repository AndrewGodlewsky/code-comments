# Password reset by emailed link

A user who cannot log in asks for a one-time reset link by email and sets a new password with it. Today the web client calls the API server, which reads and writes Postgres. An email worker sends queued emails through a mail provider. The reset adds a `reset_tokens` table and three API calls, Request link, Check link and Set password. The link is checked twice, when the page loads and again at submit, so a dead link never shows a form and a link used in between still fails. The request writes the link and its email job in one transaction, so a link never exists without its email, and the API replies before any email is sent.

## Terms

- **Token**: 32 random bytes the API makes for each link. It is URL-safe text and appears only inside the link and in the queued email job.
- **Token hash**: the SHA-256 of the token, a one-way scramble. Only the hash is stored, so a leaked table does not reveal a working link.
- **reset_tokens**: new Postgres table with one row per link issued. Columns: `user_id`, `token_hash`, `created_at`, `expires_at` (30 minutes after `created_at`) and `used_at` (empty until the link is used or replaced).
- **Valid link**: a `reset_tokens` row whose `used_at` is empty and whose `expires_at` has not passed. A valid check also gives the account, through the row's `user_id`.
- **Rate limit**: at most 3 `reset_tokens` rows per account in any rolling hour. Used and replaced rows still count, so no separate counter is needed. Per-IP limits are not part of this design.
- **users**: existing table. Holds the password hash.
- **sessions**: existing table with one row per logged-in device. The API checks it on every request, so deleting an account's rows logs that account out everywhere.
- **Email queue**: a holding table for outgoing email jobs. A job holds the recipient, the email type and, for a reset email, the link. This design assumes the queue is a Postgres table. See Open questions.
- **Email worker**: the process that takes a job from the queue and sends it through the mail provider.
- **Mail provider**: the third-party service that delivers the email.
- **Backoff**: the growing wait between retries. The existing worker sets the delays.
- **Row lock**: other requests on the same user row wait until the current transaction ends. This stops two requests from both passing the rate limit.
- **Hidden field**: a form input the user does not see. The page sends it back with the form.
- **Breached-password list**: passwords found in past data leaks. A new password must not be on it.

## Diagram

```
 Browser ---> API server ---> Postgres
                 |            (users, sessions, reset_tokens, email queue)
                 |
                 +---> Email queue ---> Email worker ---> Mail provider

 1. Request:    email -> [one transaction: lock user row, count last hour,
                          mark older tokens used, insert token, queue email]
                -> same reply for every address
 2. Send:       queue -> worker -> mail provider (up to 3 retries, then drop)
 3. Open link:  token -> hash -> link check -> password form
                                            or "link expired" page
 4. Set:        token check -> password check -> [one transaction: mark token
                used, save password hash, delete sessions] -> queue
                "password changed" email -> login page
```

The email queue is the Postgres table in the first box. This is assumed, not confirmed.

## Steps

1. **Request a link.** Starts when the user submits their email on the "Forgot password?" form. The form calls Request link. The API server runs parts a to e in one database transaction. It holds the account's row lock until the transaction commits or rolls back. The lock stops two requests from both counting 2, both inserting and both passing the limit of 3.
   a. Look up the address in `users`. If there is no account, skip to part f. Nothing is written and nothing is sent.
   b. Lock the account's user row, then count its `reset_tokens` rows created in the last hour. If the count is 3 or more, skip to part f. Nothing is written and nothing is sent.
   c. Mark every older unused token for this user as used. This kills it, so it fails the link check. The rows stay, so they still count toward the limit.
   d. Insert a new `reset_tokens` row with the hash of a new token, `created_at` set to now and `expires_at` set to 30 minutes later.
   e. Insert an email job into the queue in the same transaction. The job holds the recipient, the email type and the link, which contains the raw token. A token row never exists without its job, and a job never exists without its token row.
   f. Commit, then reply: "If an account exists for that address, we've sent a link." Unknown addresses and requests over the limit get the same reply. The API does not wait for the mail provider.
   If any read or write in parts a to e fails, or the commit fails, the whole transaction rolls back. There is no new row, no killed token and no job. The API returns a server error for any address. A rolled-back request uses no hourly slot, because the queue write is in the same transaction.

2. **Send the email.** Starts when a job is in the queue. The worker takes the job and sends it through the mail provider. The job holds the link until the job ends. After a successful send, the worker deletes the job, so the raw token does not stay in the queue. If a send fails, the worker makes one try plus up to 3 retries, with backoff. If the last try fails, it logs the failure and deletes the job.
   If the job is dropped, nobody is told and the user gets no email. The link still works until it expires. The user can ask again, and the failed link still counts toward the limit, because its row was committed in step 1.

3. **Open the link.** Starts when the user clicks the link in the email. The link is an address on the web client, with the token as its last part. It opens the "choose a new password" page, which sends the token to the Check link API call. The API hashes the token and runs the link check. The check runs here so that a dead link never shows a password form.
   If the link is valid, the API returns the password form with the token in a hidden field. If the link is missing, used, expired or replaced, the API shows "this link has expired, request a new one." That page does not say which reason applied. This step changes nothing in the database. If the database read fails, the API shows a server error page.

4. **Set the new password.** Starts when the user submits the form with the token and the new password. The form calls the Set password API call. The token is checked again at submit, because the link can expire, be used or be replaced after the page loaded. The API then does the following, in order:
   a. Run the link check. It finds the token's row and the account that row belongs to, through `user_id`. Every later change applies to that account. If the check fails, show the expired page. Nothing changes.
   b. Check the password. It must be at least 12 characters and must not be on the breached-password list. If it fails, the form shows the reason. The link is not changed, and the user can try again until it expires.
   c. Run the breached-password check before the transaction, because it is a read. If it cannot run, reject the password with "please try again shortly." The link is not changed. The check fails closed: it rejects rather than accepts.
   d. Start one database transaction:
      - Set `used_at` on the token only if it is still unused and not expired. If no row changes, roll back and show the expired page. This stops two submits from both succeeding.
      - Save the new password hash in `users` for the account from part a.
      - Delete every `sessions` row for that account, including the session of the device doing the reset. That device is logged out too.
   e. After the commit, queue a "your password was changed" email to the account's address in `users`, found by `user_id`. This is a separate queue write, not part of the transaction. It goes through the same queue, worker, retries and drop rule as step 2.
   f. Redirect to the existing login page. No session is created, so the user logs in with the new password.
   If the transaction in part d fails partway, it rolls back. The password is unchanged, the token is still unused and no session is deleted. The user sees an error and can retry the same link until it expires. If the queue write in part e fails, the password change still stands. The error is logged and no notice is sent.

## Open questions

- Is the existing email queue a Postgres table? This design assumes it is, and steps 1 and 4e depend on that. If it is not, the queue write cannot share the transaction. A commit failure after the queue write could then leave a job whose token does not exist. This needs a decision before build.
- The brief says the raw token is never stored, but the queued job holds the link until the worker sends it. Decide how to meet this, for example by encrypting the job or having the worker make the token. Not decided.
- The brief says the forgot-password endpoint always returns the same message. A server error on a failed write in step 1 breaks that, and it can reveal that an account exists. Should write failures return the generic message instead? That would tell the user a link was sent when it was not.
- Reply timing for known and unknown addresses is not equal. A timing difference could reveal whether an account exists.
- Per-IP limits are not in the brief. The limit counts per account only.
- If the worker drops a reset email, the user is not told. Should someone be alerted?
- If the worker crashes mid-send, the job may be picked up again, and the user could get the same email twice. This depends on how a job is marked taken or finished, which is not decided.
- The breached-password check may be a local list or an outside service. If it is a service, the failure handling in step 4c depends on that.
- If the "password changed" email is dropped, the user gets no notice. This follows the same rule as step 2.
- Not decided here: how the worker learns a job exists (push or poll), how a job is marked taken or finished, the backoff values, the password hash algorithm, the host and path of the link, and the wording of the "password changed" email.