# Password reset by emailed link: design

## Summary

A user who cannot log in asks for a reset link by email. The API creates a one-time link that works for 30 minutes. The database stores only a fingerprint of the link, and the email goes through the existing email queue. The user opens the link, sets a new password, and is logged out on every device. The design adds one table. Row locks stop concurrent requests from issuing more than 3 links per hour or using one link twice.

Today the API keeps `users` and `sessions` in Postgres. To send an email, the API adds a job to an email queue, and a worker sends it. If delivery keeps failing, the worker drops the job and nobody is told.

## Terms

- **Raw token**: 32 random bytes, encoded as URL-safe text (letters, digits, `-` and `_`). It appears only in the email link and in the email job. The API never stores it.
- **Token hash (SHA-256)**: a fixed one-way fingerprint of the raw token. The table stores this hash, so a leaked table gives no working links.
- **Password hash (argon2id)**: a slow one-way scramble of the password. Only the hash is stored.
- **token_id**: the database id of one row in `password_reset_tokens`. The email job carries it.
- **Email queue**: the list of mail jobs the API adds to. It already exists. Whether it is stored in Postgres is not known yet (see Open questions).
- **Email worker**: a background process that takes jobs off the queue and sends them.
- **Mail provider**: the third-party service that delivers the email.
- **Row lock (`FOR UPDATE`)**: a lock on one database row. Other requests that need the row wait until the transaction ends.
- **Rolling hour**: the 60 minutes before now, not a clock hour.
- **Used**: a link that has completed a reset. The row stays in the table.
- **Invalidated**: marked as no longer usable. The row stays in the table.
- **Session**: one row in `sessions` per logged-in device. The API checks it on every request.
- **Breached-password list**: passwords seen in public data leaks. These are refused. A local copy lives inside the API server.
- **Edge**: the front door in front of the API, such as a load balancer or gateway. Per-IP limits are set here.
- **Referer header**: the browser's record of the page that linked to the current page. Browsers send it with requests.
- **Referrer-Policy: no-referrer**: a response header that stops the browser from sending the Referer header.
- **history.replaceState**: a browser call that changes the address bar text without reloading the page.
- **422 and 302**: HTTP status codes. 422 means the request was rejected for its content, here a form error. 302 is a redirect.

## 1. Request flow: `POST /password/forgot` with `{ email }`

```
[Web client] --POST /password/forgot {email}--> [API server]
                                                     |
                             normalise email, look up users.email
                                                     |
                     no such user? ---- yes ---------+---> RESPOND
                                                     | no
                             generate raw token (32 random bytes)
                                                     |
                             BEGIN; SELECT users WHERE id = ? FOR UPDATE
                                                     |
                             count password_reset_tokens
                               WHERE user_id = ? AND created_at > now() - 1 hour
                                                     |
                             count >= 3? ---- yes ---> ROLLBACK --> RESPOND
                                                     | no
                             UPDATE password_reset_tokens SET invalidated_at = now()
                               WHERE user_id = ? AND used_at IS NULL
                                 AND invalidated_at IS NULL
                                                     |
                             INSERT password_reset_tokens
                               (user_id, token_hash = sha256(raw),
                                expires_at = now() + 30 min)
                                                     |
                             COMMIT
                                                     |
                             enqueue email job { to, token_id, raw token }
                                                     |
                                                  RESPOND
                                                     |
                             200 OK "If an account exists for that address,
                                     we've sent a link."
                             (same status, body and headers on every branch)
```

Steps:

1. **Look up the address.** This starts when the forgot form posts an email. The API normalises the email and looks it up in `users`. If there is no account, skip to step 8. Nothing is written and nothing is sent.
2. **Make the raw token.** The API creates 32 random bytes from a cryptographic random source and encodes them as URL-safe text. This runs before the transaction, so the lock is held for less time. If this fails, return a server error. Nothing is written.
3. **Lock the account.** Start a transaction and lock the user's row in `users`. The lock makes parallel requests for one account wait for each other. Without it, two requests could both count 2 and both issue a link, which takes the account past 3 per hour. If the lock fails, roll back and return a server error.
4. **Count issued links.** Count this user's `password_reset_tokens` rows created in the last rolling hour. Used and invalidated rows count, because they were issued. If the count is 3 or more, roll back and go to step 8. So the 3rd link in an hour is allowed, and the 4th request is refused. A refused request writes nothing, so it cannot invalidate the earlier link.
5. **Retire older links.** Mark every earlier unused link for this account as invalidated. A new link kills any earlier unused link. If this fails, roll back and return a server error.
6. **Store the new link.** Insert one row with `token_hash = sha256(raw token)` and `expires_at = now() + 30 minutes`. The raw token is not stored. This is the only row written. If this fails, roll back and return a server error.
7. **Commit, then queue the email.** Commit first. Then add the job `{ to, token_id, raw token }` to the email queue, where `token_id` is the new row's id. The job carries `token_id` so the worker can mark the row if the send is dropped, without a hash lookup. The id is not secret, and the raw token still stays out of the table. Queuing after commit means a queue failure cannot undo the link. The worker sends the job through the mail provider.
8. **Respond.** Return 200 with the generic message once the branch is decided. Unknown accounts and over-limit requests both reach this step. The status, body and headers are the same on every branch, and nothing in them reveals which branch ran. Response timing can still differ (see Open questions).

## 2. Link-click flow: `GET /password/reset?t=...`, then `POST /password/reset`

```
GET /password/reset?t=<token>        (from the email link)
  sha256(t) -> find row in password_reset_tokens
  row found AND used_at IS NULL AND invalidated_at IS NULL
            AND expires_at > now() ?
     no  -> "This link has expired. Request a new one."
     yes -> show "choose a new password" form (t goes in a hidden field)

POST /password/reset {t, new_password}
  BEGIN
  1. sha256(t) -> user_id, no lock           no row -> expired page, nothing written
  2. SELECT users WHERE id = ? FOR UPDATE    (lock the user row first)
  3. SELECT password_reset_tokens WHERE token_hash = ? FOR UPDATE
       re-check used_at, invalidated_at, expires_at
       fail -> expired page, ROLLBACK
  4. new_password >= 12 characters AND not on the breached list
       fail -> form error, ROLLBACK, link still valid
  5. UPDATE users SET password_hash = argon2id(new_password)
  6. UPDATE password_reset_tokens SET used_at = now()
  7. DELETE FROM sessions WHERE user_id = ?  (every device, this one included)
  COMMIT
  enqueue "your password was changed" email
  302 redirect to /login, no session created, session cookie cleared
```

Steps:

1. **Check on page load.** This starts when the user opens the email link. The API hashes `t` and looks up the row. If every check passes, it shows the form. Otherwise it shows the expired page. Loading changes nothing and burns nothing. The load check only chooses the page.
2. **Carry the token into the form.** The form sends `t` in a hidden field. After the page loads, the browser removes `t` from the address bar, so `t` travels only in the POST body.
3. **Check again on submit.** The API runs the transaction shown in the diagram. The submit check decides the reset, not the load check.
   - Step (1) finds the user by hash, without a lock. If no row matches, show the expired page. Nothing is written.
   - Steps (2) and (3) lock the user row, then the token row. This order is always used. The request flow also locks the user row first, so the two flows cannot deadlock. A double submit waits on the token lock. The first commit wins. The second sees `used_at` set and gets the expired page. So only one password change can happen per token.
   - Step (4) runs before any write. If the password is rejected, roll back. The server shows the form again with the error and the same `t` in its hidden field, so the user can retry. The link stays usable until it expires. If the breached-password list cannot be loaded, show a form error asking the user to retry. The check fails closed.
   - Steps (5) to (7) write the new password hash, mark the link used, and delete all of the user's `sessions` rows, including this device. Deleting sessions takes effect at once, because every request checks sessions. Any error before COMMIT, including a database error, rolls back. The password and the link stay as they were.
4. **After commit.** Queue the "your password was changed" email. Then redirect to `/login`. No session is created, so the user logs in again on purpose. The session cookie is cleared because its session row was just deleted. This stops the browser from sending a dead cookie.

Rules for the reset pages:

- Send `Referrer-Policy: no-referrer` on both reset pages, so the browser does not pass the token on in the Referer header.
- After load, remove `t` from the address bar with `history.replaceState`.
- Never log query strings for these routes.
- After load, the token travels only in the POST body.

## 3. What happens when things fail

| Trigger | What the user sees | What happens to state |
|---------|--------------------|-----------------------|
| Unknown email | Generic message | Nothing written, nothing sent. |
| Over the limit: 3 links already issued in the last hour, so this is the 4th request | Generic message | Nothing written, nothing sent. The earlier unused links stay valid. |
| Random source, lock, count, retire, or store step fails during the forgot request | Server error | Transaction rolls back, or nothing was written yet. No link and no email. |
| Mail provider keeps failing | Generic message. The user is never told the send failed, which is the existing behaviour. | The worker retries 3 times with backoff, then logs and drops the job. On drop it sets `invalidated_at` on the row whose id is `token_id`, emits a metric and raises an alert. The row still counts toward the limit, so a drop does not free a slot. The user can request again while under the limit. |
| Queue add fails after COMMIT | Generic message. No email arrives. | The row exists but cannot be delivered. The API logs the error with the `token_id` and emits the same metric as a dropped send, so operators see it. Nothing is retried. The row expires on its own in 30 minutes and counts toward the limit. The fix is in Open questions. |
| Link invalid, expired, used, or superseded by a newer link, at page load or on submit | "This link has expired. Request a new one." | Nothing changes. A superseded link was already invalidated by the newer request. |
| New password under 12 characters, or on the breached list | Form error on the same form, with the same `t` in its hidden field. The user can retry. | The token is untouched. The link stays valid until it expires. |
| Breached-password list cannot be loaded | Form error asking the user to retry | The list is a local copy in the API server, so there is no live call. Fail closed. Nothing is written. |
| Two submits with the same token at once | One success, one expired page | The token-row lock lets one commit win. Exactly one `used_at` is set. |
| Database error during reset | "Something went wrong, try again." | The transaction rolls back. The password is unchanged and the token is not burned. |
| "Your password was changed" email fails to send | Nothing. The reset itself succeeded. | The worker retries and drops the job the same way as above, except nothing is marked, because the link is already used. Log it. Do not roll back the reset. |
| Token guessing | Nothing | A 256-bit token cannot be guessed in practice. Both endpoints are rate-limited per IP at the edge. |
| Token leaks through the Referer header or logs | Nothing | Reset pages send `Referrer-Policy: no-referrer`. `t` is removed from the address bar after load. Query strings are never logged. The token is sent only in the POST body. |

## 4. Data

One new table. Nothing else is stored.

```
password_reset_tokens
  id              bigint  PK
  user_id         bigint  FK users(id) ON DELETE CASCADE, indexed with created_at
  token_hash      char(64)  UNIQUE          -- sha256 of the 32-byte raw token, hex
  created_at      timestamptz
  expires_at      timestamptz               -- created_at + 30 min
  used_at         timestamptz NULL          -- set when the reset succeeds
  invalidated_at  timestamptz NULL          -- set when a newer link supersedes it, or on drop
```

Rules:

- The raw token is never stored in this table. It exists only in the email link and in the email job payload. The payload stays in the queue until the job is sent or dropped.
- Used and invalidated rows stay in the table until cleanup. They still count toward the rate limit.
- A periodic cleanup deletes rows with `created_at` older than 1 hour, the length of the rate-limit window. Validity is still enforced by `expires_at`. How the cleanup is scheduled is in Open questions.
- On a successful reset, `users.password_hash` is overwritten and the user's `sessions` rows are deleted. No other schema change is needed.

## Open questions

1. **Breached-password list.** Decided: a local copy inside the API server, not a live service call. Not decided: where the list comes from and how often it is refreshed.
2. **Failed sends and the limit.** Should the 3-per-hour count include links whose sends failed? The current design counts them. Counting only delivered mail would need delivery callbacks from the mail provider.
3. **Telling the user about a dropped send.** Today the user is not told. This design keeps that behaviour and flags it for the owner.
4. **Raw token in the email job, and the queue add failure.** The email needs the raw token, so the raw token sits in the job until it is sent or dropped. Option (a): encrypt the job payload at rest, and delete it on completion or drop. Option (b): use a transactional outbox. The job is written in the same transaction as the token row, so a failed queue add cannot leave an undeliverable token. Option (b) is cleaner if the queue lives in Postgres. It is not known yet where the queue stores jobs today. Otherwise, do both.
5. **Other credentials.** Should refresh tokens and API keys also be revoked on reset, beyond sessions? If the system has them, revoke them in the same transaction as the reset.
6. **Response timing.** The unknown-account branch skips the transaction and the queue add, so it returns faster. The brief's same-response rule covers body, status and headers only. This timing gap is a real leak that this design does not close. The owner should decide whether to equalise timing.
7. **Cleanup schedule.** Is there an existing scheduled job in the API that can run the 1-hour purge, or does it need a new one? Not known from the brief.
