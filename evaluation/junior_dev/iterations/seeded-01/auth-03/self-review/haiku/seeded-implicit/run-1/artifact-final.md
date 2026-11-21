# Password reset by emailed link

## Goal

A user who cannot log in enters their email address and receives a one-time link. The link opens a page where they choose a new password.

The design covers three flows and the ways each one can fail:

1. **Request a link.** The user submits their email address.
2. **Open the link.** The user clicks the link in the email.
3. **Submit a new password.** The user sends the new password through the form.

## Terms used here

- **Hash (SHA-256)**: a one-way scramble of a value. The same input always gives the same output, but the output cannot be turned back into the input. We store hashes so that a leaked database does not reveal anything usable.
- **Transaction**: a group of database writes that either all happen or none happen.
- **Row lock**: while one transaction holds a lock on a row, any other transaction that needs that row waits until the lock is released. The lock is released when the transaction ends.
- **Conditional update**: an update that changes a row only if a condition is still true at the moment of the update. The database reports how many rows changed. Here the answer is 0 or 1.
- **Rolling hour**: the hour that ends now. It moves with the clock, so there is no fixed reset time.
- **Breached-password list**: a list of passwords that have appeared in public data leaks. A new password on this list is refused.
- **Session**: one row per logged-in device. The API checks the session on every request. Deleting the row logs that device out.
- **Queue and worker**: the API adds a job that describes one email to the queue. A separate worker takes jobs from the queue and sends them.
- **Hidden field**: a form input that the browser keeps and sends back with the form, but does not show to the user.

## Parts

- **Browser**: the web app the user sees.
- **API server**: receives every request and makes all the decisions.
- **Postgres**: the database. Three tables matter here:
  - `users`: one row per account. It holds `password_hash`, a hash of the password. The real password is never stored.
  - `sessions`: one row per logged-in device.
  - `reset_tokens` (new): one row for each reset link ever issued. Columns: `id`, `user_id`, `token_hash` (unique), `created_at`, `expires_at`, `used_at`, `revoked_at`.
- **Email queue**: a list of pending emails. The API adds a job for each email.
- **Email worker**: takes jobs from the queue and sends them through the mail provider. If a send fails, it retries up to 3 times with growing delays. After that it logs the failure and drops the job. Nobody is told.
- **Mail provider**: the third-party service that delivers the email.

## System diagram

```
   Browser ----> API server ----> Postgres
                    |             users          password_hash
                    |             sessions       one row per logged-in device
                    |             reset_tokens   one row per link issued
                    |
                    +----> Email queue ----> Email worker ----> Mail provider
```

## Flow 1: Request a link

```
 FLOW 1: Request a link   (POST /forgot-password with an email address)

 Browser            API server                               Postgres / queue
 -------            ----------                               ----------------
 email -----------> 1. Look up the user with that email
                       no such user? ----------------------> stop, write nothing
                    2. In one transaction, lock the user's
                       row, then count the reset_tokens rows
                       for this user created in the last hour
                       3 or more? -------------------------> stop, write nothing
                    3. Same transaction, continuing:
                       - make 32 random bytes (the token)
                       - insert a row with SHA-256(token)
                         and expires_at = now + 30 minutes -> reset_tokens
                       - mark older unused rows revoked ---> reset_tokens
                       - add an email job that holds the
                         link with the raw token ----------> Email queue
 <---------------- 4. Reply on every path above:
                      "If an account exists for that address,
                       we've sent a link."
```

Notes:

- Steps 2 and 3 run in one transaction. The row lock on the user's row is held until the transaction ends. If a second request for the same user arrives at the same moment, it waits. When it goes ahead, it counts the rows the first request just wrote. This stops two requests from both passing the limit.
- The user's row exists for every account, so locking it serializes all reset requests for that account.
- The reply in step 4 is the same on every path. The user cannot tell from it whether an account exists or whether the limit was hit.

## Flow 2: Open the link

```
 FLOW 2: Open the link   (GET /reset?token=...)

 Browser            API server                               Postgres
 -------            ----------                               --------
 click link ------> Take the token from the link and
                    compute SHA-256(token)
                    Look for a reset_tokens row with that hash
                    where used_at and revoked_at are empty
                    and expires_at is in the future --------> reset_tokens
 <----- found:      "Choose a new password" form.
                    The raw token goes in a hidden field.
 <----- not found:  "This link has expired.
                    Request a new one."
                    (same page for expired, used,
                     replaced, or made-up tokens)
```

Notes:

- The server looks up the hash, never the raw token, so the database never holds anything that works as a link.
- The server never tells the user why a link failed. Expired, used, replaced and invented tokens all get the same page.

## Flow 3: Submit a new password

```
 FLOW 3: Submit new password   (POST /reset with token + new password)

 Browser            API server                               Postgres / queue
 -------            ----------                               ----------------
 token + password -> A. Check the token again, as in Flow 2
                       not valid? -------------------------> expired page
                    B. Check the password:
                       under 12 characters, or on the
                       breached-password list?
 <----- form again with an error. The link is NOT used up.
                    C. One transaction:
                       1. Mark the token used, only if it is
                          still unused, not revoked and not
                          expired. If 0 rows changed, stop
                          and show the expired page. ------> reset_tokens
                       2. Save the new password hash ------> users
                       3. Delete every session for this user -> sessions
                       4. Add a "password changed" email job -> Email queue
 <----- redirect to the login page (no automatic login)
```

Notes:

- The raw token travels back in the hidden field. It is the same token that was in the link.
- Steps A and C1 both check that the token is still valid. Step A gives a fast answer so the page can show the right message. Step C1 is the real guard. It is one conditional update, so if two submits race, only one can change the row, and only that submit continues.
- If the password is rejected at step B, nothing is written and the link stays usable until it expires.
- If step C1 changes 0 rows, the transaction stops. Steps 2 to 4 never run.

## Rules

- **Token**: 32 random bytes. The raw token exists only inside the emailed link and in the hidden field of the form. The database stores only its SHA-256 hash, so a database leak does not expose usable links.
- **Lifetime**: 30 minutes from the moment the link is issued. A link works once.
- **Replacement**: issuing a new link marks earlier unused links for the same account as revoked. This happens in the same transaction as the insert, so there is never a moment when two links both work.
- **Rate limit**: at most 3 links per account in any rolling hour. Each `reset_tokens` row is one email, so the limit counts rows. Revoked rows still count. Example: an account that requests 3 links in ten minutes and asks again must wait until the oldest of those rows is more than an hour old. Over the limit, the server still gives the generic reply, but writes nothing and sends nothing.
- **Generic reply**: the same text for every outcome of Flow 1.
- **Password rule**: at least 12 characters, and not on the breached-password list. A rejected password does not use up the link.
- **Single use under races**: marking the token used is one conditional update ("only if still unused, not revoked and not expired"). If two submits race, only one succeeds.
- **After a successful reset**: the new hash is saved, the link is marked used, and all sessions for the account are deleted. These three changes and the queued confirmation email share one transaction, so either all of them happen or none do. Deleting the sessions also logs out the device that made the reset. The user goes to the login page and is not logged in automatically.
- **Logging**: never log the raw token or the full reset link.

## Failure paths

| Situation | What happens | What the user sees |
|---|---|---|
| Address has no account | No row, no email | Generic message |
| Account already has 3 links in the last hour | No row, no email | Generic message |
| Email send fails 3 times | The worker logs and drops the job. The link stays valid, but the user never receives it. Nobody is alerted. Each new request counts toward the hourly limit. | Generic message, then no email |
| Queue unavailable after the link row is written | The row exists but no email is sent. The result is the same as a dropped email. If the queue lives in Postgres, write the row and the job in one transaction so that both happen or neither does. A separate queue service can still produce this case. | Generic message |
| Link expired, used, or replaced | Rejected when the page loads and again on submit | "This link has expired. Request a new one." |
| Weak or breached password | Nothing is saved. The link stays valid. | Form error, try again |
| Link expires while the form is open | Submit is rejected. The password does not change. | Expired page |
| Two submits with the same link | One succeeds. The other changes 0 rows in step C1 and is rejected. | Expired page for the second submit |
| Confirmation email fails | The password has already changed. The email is dropped after retries. | Login page as normal |

## Open gap

Dropped emails are silent. A user whose reset email is dropped gets no notice and must ask again. Alerting on dropped reset or confirmation jobs is a possible follow-up. It is not part of this design.