# Password reset by emailed link: design

## Summary

A user who cannot log in can ask for a reset link from a "Forgot password?" form. The server always gives the same reply, so the form never shows whether an email address has an account.

If the account has fewer than 3 reset links in the last hour, the server makes a one-time link that works for 30 minutes. It stores only a hash of the link's token and queues an email that holds the link. Opening the link shows a form and changes nothing. Submitting the form checks the link again under a database row lock. Then it saves the new password, uses up the link, logs the account out on every device, and queues a "password changed" email. The user is sent to the login page and must log in again.

The shape follows from three facts. The reply is the same on every path, so the response does not leak account data. Sending email is slow and can fail, so it runs in the background. Reading the link changes nothing, so mail scanners that open links cannot use it up.

How the system works today: the web client calls the API server. The API keeps accounts in the `users` table and logged-in devices in the `sessions` table, both in Postgres. It checks `sessions` on every request, so a device with no row is logged out. Outgoing email is added as a job to an email queue. An email worker takes each job and sends it through the mail provider. If a send fails, the worker retries up to 3 times, waiting longer each time (backoff). Then it logs the failure and drops the job. Nobody is told.

## Terms

- **Token**: 32 random bytes, written as text (base64url). It appears only inside the emailed link.
- **Token hash**: the SHA-256 of the token. SHA-256 is a fixed one-way scramble, so the hash cannot be turned back into the token. Only the hash is stored in `password_resets`.
- **Link**: one row in `password_resets`. Each issued token has one link.
- **Active link**: a link whose state is `active` and whose `expires_at` is later than now.
- **Email queue**: the list of emails waiting to be sent.
- **Worker**: the existing email worker. It takes jobs off the queue and sends them.
- **Mail provider**: the outside service that delivers the email.
- **Outbox row**: a row written in the same transaction as a state change, saying send this email. Used only if the queue is not stored in Postgres.
- **Relay**: a small process that copies outbox rows into the queue. Used only with an outbox. It does nothing else.
- **Transaction**: a group of database writes that all succeed or all fail together.
- **Row lock (`FOR UPDATE`)**: one transaction holds a row until it ends. Any other transaction that needs that row waits.
- **Session row**: one row in `sessions` for one logged-in device. No row means that device is logged out.
- **Rolling hour**: the 60 minutes before now.
- **Breached-password list**: a list of passwords seen in past data leaks. We check against a copy we keep ourselves.
- **Argon2id**: the slow hashing method that turns a password into the stored hash.
- **CSPRNG**: a random number generator designed to be unpredictable. Used to make the token.

## Diagram

```
PASSWORD RESET BY EMAILED LINK

  BROWSER = web client     API = API server     DB = Postgres
  WORKER  = email worker   MAIL = mail provider


=== REQUEST: POST /password-reset  { email } ===================================

  BROWSER --- email ---> API
                          |
                          | 1.1 Trim and lowercase the email. BEGIN.
                          |     Find the user and lock its row in one statement:
                          |       SELECT id FROM users WHERE email = ? FOR UPDATE
                          |     No row: COMMIT, go to the reply.
                          |     Concurrent requests for the same account wait here.
                          |
                          | 1.2 Count links issued in the last hour, any state:
                          |       SELECT count(*) FROM password_resets
                          |       WHERE user_id = ? AND issued_at > now() - 1h
                          |     3 or more: COMMIT, write nothing, go to the reply.
                          |
                          | 1.3 Create the token: 32 random bytes (CSPRNG),
                          |     base64url-encoded. This is the raw token.
                          |     Store only its SHA-256 hash as token_hash.
                          |
                          | 1.4 Revoke older active links for this user:
                          |       UPDATE password_resets SET state='revoked'
                          |       WHERE user_id = ? AND state='active'
                          |     Insert the new row: token_hash, state='active',
                          |       expires_at = now() + 30 min
                          |
                          | 1.5 Write the email job, which holds the link with the
                          |     raw token, in the same transaction. If the queue
                          |     is not in Postgres, write an outbox row instead.
                          |
                          | 1.6 COMMIT
                          |
                          v
                   200 'If an account exists for that address,
                        we've sent a link.'   (same text on every path)


=== OPEN LINK: GET /reset/{token}  (read only; never uses the link) ============

  BROWSER --- GET /reset/{token} ---> API
                                       | 2.1 SHA-256 the token from the URL.
                                       | 2.2 Look for a row with that token_hash,
                                       |     state='active' and expires_at > now().
                                       |
                                       +-- found --> 200 'choose a new password'
                                       |             form. Token in a hidden field.
                                       |
                                       +-- not found (never issued, used,
                                                      revoked or expired)
                                                  --> 200 'this link has expired,
                                                      request a new one'


=== SUBMIT: POST /reset  { token, new_password } ===============================

  BROWSER --- POST ---> API
                         |
                         | 3.1 Look up the token as in step 2.2 and keep its
                         |     user_id. Not active -> 'expired' page. Stop.
                         |
                         | 3.2 Check the password: at least 12 characters and
                         |     not on the local breached list. If rejected, show
                         |     the form again with an error, token in the hidden
                         |     field. Nothing is written. The link stays active.
                         |
                         | 3.3 Hash the new password (argon2id), outside the
                         |     transaction.
                         |
                         | 3.4 BEGIN
                         |       SELECT id FROM users WHERE id = ? FOR UPDATE
                         |         (the user_id from step 3.1: lock users first)
                         |       SELECT ... FROM password_resets
                         |         WHERE token_hash = ? FOR UPDATE
                         |     Check state='active' and expires_at > now().
                         |       If not both true: ROLLBACK -> 'expired' page.
                         |     UPDATE password_resets SET state='used',
                         |       used_at = now()
                         |     UPDATE users SET password_hash = <new hash>
                         |     DELETE FROM sessions WHERE user_id = ?
                         |       (every device, including this one)
                         |     Write the 'your password was changed' email job.
                         |   COMMIT
                         |
                         v
                  302 redirect to /login. No session is created.
```

## How each step works

**Request (steps 1.1 to 1.6).** Starts when someone submits the forgot-password form with an email address.

- **1.1** Trim and lowercase the address. Then, in one transaction, find the user and lock its row. The lock makes a second request for the same account wait, so two requests cannot both pass the limit check. If no user has that address, commit and reply. Nothing is written, so unknown addresses never count toward the limit.
- **1.2** Count the links issued to this user in the last hour, in any state: active, used or revoked. Failed sends count too (see open question 4). If the count is 3 or more, commit without writing and reply. The existing link keeps working.
- **1.3** Only now make the raw token. It is made after the limit check so that no token exists for a request that issues no link. Store only its SHA-256 hash.
- **1.4** Revoke the user's older active links, then insert the new row. The new row is active and expires 30 minutes from now. This keeps only one link working at a time. It runs only when the limit allowed the request, so an over-limit request revokes nothing.
- **1.5** Write the email job in the same transaction. The job holds the link with the raw token. If the queue is in Postgres, the job is a queue row. It becomes visible only when the transaction commits. If the queue is not in Postgres, the job is an outbox row, and the relay copies it into the queue after commit. Writing the job in the same transaction means the email exists exactly when the link was committed.
- **1.6** Commit. Every path returns the same text and the same status. Sending happens later, so the response time does not depend on the mail provider.

**Opening the link (steps 2.1 and 2.2).** Starts when the user clicks the link. This page only reads. It never uses the link, so mail scanners that open links early cannot use it up.

- **2.1** Hash the token from the URL.
- **2.2** Look for an active link with that hash whose `expires_at` is later than now. If found, show the "choose a new password" form, with the token in a hidden field. If not found (never issued, used, revoked or expired), show "this link has expired, request a new one." That page is the same for all four cases, so it does not reveal which one happened. Its "request a new one" link goes to the Forgot password form.

**Submitting the new password (steps 3.1 to 3.4).** Starts when the form posts the token and the new password.

- **3.1** Look up the token as in step 2.2, and keep the link's `user_id` for step 3.4. If the link is not active, show the expired page and stop. A bad token therefore skips the slow password work.
- **3.2** Check the password. It must be at least 12 characters and not on the breached list. If it fails, show the form again with an error. The same token goes back into the hidden field, because the form was posted with it. Nothing is written, and the link stays active until it expires, so the user can try again.
- **3.3** Hash the new password with argon2id. This is slow, so it runs outside the transaction.
- **3.4** Start a transaction. Lock the account's `users` row first, then lock the link's row with `SELECT ... FOR UPDATE`. The order matches step 1.1, so a reset request and a submit for the same account cannot wait on each other in a cycle (a deadlock). Under the users lock, the second one simply waits. Check again, under the lock, that the link is active and not expired. This second check is needed because the link can change after step 3.1. It can expire, another submit can use it, or a new reset can revoke it. Only a check made under the lock can safely change the link's state. If the check fails, roll back and show the expired page. If it passes:
  - mark the link `used` and record the time,
  - save the new password hash in `users`,
  - delete every `sessions` row for this user, including this device,
  - write the "password changed" email job.

  Then commit and redirect to `/login`. The reset creates no session, so the user logs in again. The API checks session rows on every request, so deleting them logs each device out at once.

**Mail worker (runs after step 1.5).** Starts when the worker takes a job from the queue.

- For a reset email, the job holds the raw token. Before every send attempt, the first attempt and each retry, the worker takes the SHA-256 of the token and looks for the `password_resets` row with that hash. If the row is missing, is not `active`, or has expired, the worker drops the job and sends nothing, with no retry. This covers a job queued before a newer link revoked it, and a retry that runs after the link has expired. A job cannot be taken before its transaction commits, so the row exists unless it has been removed.
- The "password changed" email has no link, so the worker sends it without this check.
- Send the email through the mail provider.
- On success, delete the job. This removes the raw token from the queue.
- On failure, wait for the backoff, then go back to the first bullet and check the link again before the next try. Up to 3 retries. After the third failure, log the failure without the token, delete the job and drop it. Nobody is told.

**Token in the URL.** The token appears in access logs, browser history and the Referer header (the address of the previous page, which is sent to other sites). So the design does three things.

- Strip the token from logs. Every log that records the request path writes `/reset/[redacted]` in place of `/reset/{token}`. That covers the API access log, any proxy or load balancer log, and error logs that print the URL. The token is replaced before the line is written, so it never reaches the log store.
- Send `Referrer-Policy: no-referrer` on the reset pages.
- Load no third-party scripts there.

The form sends the token in the request body, not in the URL.

## What happens when things fail

| What goes wrong | What happens |
|---|---|
| Email address has no account | Same reply. No row, no email, no job. |
| Account already has 3 links in the last hour | Same reply. No new row and no revoke, so the existing link still works. No email. |
| Mail send fails | The worker retries 3 times with backoff, then logs and drops the job. Nobody is told. The link was never delivered and expires in 30 minutes. The user sees the same reply and may ask again, which uses another slot. |
| Old reset job still queued after a newer link | The worker finds no active, unexpired row for the token and drops the job. Nothing is sent. |
| Reset job retried after the link expired | The check before the retry finds no active, unexpired row. The worker drops the job. Nothing is sent. |
| Two submits at the same time | The users row lock makes the second one wait. It then finds state `used` and shows the expired page. |
| A reset request and a submit for the same account at the same time | Both lock the `users` row first, so one waits for the other. There is no cycle, so no deadlock. |
| Weak or breached password | Form error. The link is untouched and still usable. |
| Link expires while the form is open | The submit finds it expired and shows the expired page. Nothing is written. |
| API crashes before COMMIT | The transaction rolls back. No link and no job. |
| API crashes after COMMIT | The job was written in the same transaction, so the queue or relay still sends it. |
| A login races with the reset | A new session row may survive the DELETE (see open question 9). |

## Data

**`password_resets`**: one row per link.

- `id`: primary key.
- `user_id`: the account, a foreign key to `users.id`.
- `token_hash`: 32 bytes, unique. The SHA-256 of the raw token. The unique index makes the lookup fast.
- `state`: `active`, `used` or `revoked`.
- `issued_at`: when the link was made, from the database clock.
- `expires_at`: `issued_at` plus 30 minutes.
- `used_at`: when the link was used. Empty until then.
- Index on (`user_id`, `issued_at`): used by the rate-limit count.

Not stored in `password_resets`: the raw token, a copy of the email address, or the password. The raw token is kept in one other place: the email job, until the job is deleted (see open question 8).

Changed in existing tables: `users.password_hash` is overwritten on reset. The user's `sessions` rows are deleted on reset.

Cleanup: rows older than 24 hours are deleted. The rate limit looks back only one hour, so it never needs a row that the cleanup removes. What runs the cleanup is an open question.

## Open questions

1. Is the existing email queue stored in Postgres? If not, the outbox and relay described above are needed. If it is, they are not.
2. What runs the daily cleanup of rows older than 24 hours? This is not chosen yet. A daily scheduled DELETE is the simplest option if the stack has a scheduler.
3. After 3 failed sends, the user loses one of their 3 hourly slots for an email that never arrived. Recommended: the worker writes a `send_status` column on `password_resets`, and ops alerts on the failure rate. This is for ops, not a user notice.
4. Failed sends count toward the quota. This is the simplest rule, and it protects the mail provider. The alternative counts only delivered links. It needs a delivery-status write from the worker.
5. The breached-password check uses a local list. An online lookup would send the candidate password to a third party.
6. One link allows unlimited password tries until it expires. Brute force on the token is not practical, but confirm that unlimited password retries are acceptable.
7. The unknown-address branch could wait a fixed minimum time so that its timing matches the known-address branch. Not decided.
8. The brief says the raw token is never stored, but the email job must hold it until the email is sent. This design keeps it in the queue row until the job is deleted. Confirm that this is acceptable, or choose another way to deliver the link.
9. A login that checked the old password just before the reset can commit a new session row after the reset's DELETE, and that session survives. The design does not prevent this. A fix needs the login path to lock the same `users` row before it creates a session. The brief does not cover login.
10. The login page shows no notice that the password changed. The brief asks for none, and the email is the only notice. Confirm whether the login page should say so.