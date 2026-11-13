# Password reset by emailed link: design

## What this is

A "Forgot password?" flow for the consumer app. A user who cannot log in enters their email address. If an account exists and has not hit its send limit, the system emails a one-time link that is valid for 30 minutes. The link opens a page where the user chooses a new password.

Today, the web client calls the API server. The API server keeps data in Postgres: `users` (including the password hash) and `sessions` (one row per logged-in device, checked on every request). Outgoing email goes through a queue. The API adds a job, and an email worker sends it through our mail provider. If sending fails, the worker retries up to 3 times, then logs the failure and drops the job. Nobody is told.

The design has three flows: request a link, open the link, and submit a new password. The API never creates or sends the link itself. It records the send and queues a job, and the worker creates the token and emails the link. The reason: queues store job payloads, so a link in a job would store the raw token. Only the token's hash is stored anywhere.

## Terms

- **Token**: 32 random bytes. It appears only inside the reset link. It is never stored, and never put in a queue job.
- **Token hash**: the SHA-256 of the token. This is the only form the system stores.
- **Reset link**: `https://<app>/reset?t=<token>`.
- **password_reset_tokens**: one row per account. It holds the current link's hash, its expiry time and its used time. Issuing a new link overwrites the row.
- **reset_sends**: one row per reset email requested. It is used to count sends for the hourly limit.
- **Row lock (`SELECT ... FOR UPDATE`)**: locks one user's row, so concurrent requests for that account wait their turn.
- **Atomic UPDATE**: one SQL statement that checks a row and changes it in a single step. Two requests cannot both succeed with it.
- **Outbox job**: a queue job written in the same database transaction as a data change. Both commit, or neither does.
- **Breached-password list**: a list of known leaked passwords, stored locally in the API. It is never sent to anyone.
- **Enumeration**: an attacker working out which emails have accounts by comparing responses. The design makes the responses look the same.

What is stored:

- `password_reset_tokens`: `user_id` (primary key, foreign key to `users`), `token_hash` (unique, 32 bytes), `expires_at`, `used_at` (empty until the link is used). Rows older than expiry plus 24 hours are purged.
- `reset_sends`: `id`, `user_id`, `sent_at`, with an index on `(user_id, sent_at)`. Rows older than 1 hour are purged.
- Queue job payloads: `user_id` and `send_id` only. No token.
- `users`: only `password_hash` changes.
- `sessions`: the user's rows are deleted on a successful reset.

## Diagram

```
 REQUEST: POST /password-reset {email}

   Browser --> API server
                1. Find the user by normalised email.
                   No user: skip to the reply (step 6).
                2. BEGIN. Lock the user's row (FOR UPDATE).
                3. Count reset_sends for this user in the last hour.
                   3 or more: ROLLBACK, skip to the reply.
                4. Insert a reset_sends row (sent_at = now).
                   Add a queue job {user_id, send_id}. No token in it.
                5. COMMIT.
                6. Reply 200 with the generic message. Same body and
                   same minimum time on every path.
                               |
                               v
                         Email queue
                               |
                               v
                         Email worker
                   a. Make a token (32 random bytes). hash = SHA-256(token).
                   b. Upsert password_reset_tokens for this user:
                      new token_hash, expires_at = now + 30 min, used_at cleared.
                   c. Send email with https://<app>/reset?t=<token>.
                   d. If sending fails: retry up to 3 times with backoff,
                      then log and drop the job.

 LINK CLICK: GET /reset?t=<token>

   Browser --> API server: hash = SHA-256(t)
                 Find a row where token_hash = hash,
                 used_at is empty and expires_at > now.
                 No row: "This link has expired, request a new one" page.
                 Row:    "Choose a new password" form
                         (token in a hidden field).

 SUBMIT: POST /reset {t, password}

   Browser --> API server
                 1. hash = SHA-256(t). Check the row is still valid.
                    Not valid: expired page.
                 2. Password at least 12 characters and not on the
                    breached list. Rejected: show the form again.
                    Link NOT used up.
                 3. BEGIN
                 4. One atomic UPDATE: set used_at = now() where the
                    hash matches, the link is unused and not expired.
                    Returns user_id. 0 rows: ROLLBACK, expired page.
                 5. Store argon2id(password) in users.password_hash.
                 6. Delete every sessions row for this user (all devices,
                    including this one).
                 7. Add a "password changed" outbox job.
                 8. COMMIT
                 9. Redirect (303) to /login. Set no session cookie.
```

## Steps

### Request a link

1. Starts when someone submits an email on the forgot-password form. The API looks up the user by normalised email. If there is no user, go to step 6.
2. Start a transaction and lock the user's row. This makes concurrent requests for one account run one at a time.
3. Count the user's `reset_sends` rows from the last hour. If there are 3 or more, roll back and go to step 6. No link is made and no email is queued.
4. Insert a `reset_sends` row, then add a queue job `{user_id, send_id}`. The job holds no token. The send counts against the limit now, even if it fails later.
5. Commit.
6. Reply 200 with "If an account exists for that address, we've sent a link." Every path returns the same body after the same minimum time. Pad the response to a fixed minimum time, so an attacker cannot tell the cases apart.

### Send the email (worker)

1. Starts when the worker takes the job. The worker makes a new token and computes its hash.
2. Upsert the user's `password_reset_tokens` row with the new hash, `expires_at = now + 30 minutes`, and `used_at` cleared. This kills the previous link.
3. Send the email with the reset link.
4. If sending fails, retry up to 3 times with backoff. Then log the failure and drop the job. Nobody is notified.

### Open the link

1. Starts when the user clicks the link. The browser sends the token. The API hashes it and looks for an unused, unexpired row with that hash.
2. No row: show "This link has expired, request a new one."
3. Row found: show the "Choose a new password" form. The token goes in a hidden field, so the form posts it back.

### Submit a new password

1. Starts when the form is posted. The API hashes the token and checks the row is still valid. If not, show the expired page.
2. Check the password: at least 12 characters, and not on the breached list. If it fails, show the form again with an error. The link is not used up, so the user can retry until it expires.
3. Start a transaction.
4. Run one atomic UPDATE that marks the link used, but only if it is still unused and unexpired. It returns the `user_id`. If it changes 0 rows, roll back and show the expired page. This is what stops two submissions from both succeeding.
5. Store the argon2id hash of the new password in `users.password_hash`.
6. Delete every `sessions` row for the user. This logs the user out on every device, including the one that made this request.
7. Add the "password changed" email as an outbox job in the same transaction.
8. Commit.
9. Redirect (303) to `/login`. Set no session cookie. The user logs in again by hand.

## What happens when things fail

| Situation | What happens | Who is told |
|---|---|---|
| Unknown email | No row and no job. Same reply and timing as a known email. | Nobody |
| More than 3 sends in the last hour | No `reset_sends` row and no new token. The existing link stays valid. | Nobody (same generic reply) |
| Email send fails, or the worker crashes | Retried 3 times, then dropped and logged. If the crash came after the token was made, the new token already replaced the old one, so no stale link is live. The user can request again, which uses one slot. | Nobody. The user was told a link was sent, and got none. Alert on dropped jobs and give support a runbook. |
| Link opened after 30 minutes, after use, or after a newer link was issued | Expired page when opened. Expired page on submit, because step 4 changes 0 rows. | Expired page |
| Double submit or two tabs | The second submission changes 0 rows and gets the expired page. The first password is the one that takes effect. | Second submission sees the expired page |
| Weak or breached password | Form shown again with an error. The link stays usable until it expires. | Form error |
| Database error during submit | Steps 3 to 8 are one transaction. It rolls back, so the password does not change and the link is not used up. | User sees an error page (exact page not yet specified) |
| "Password changed" email dropped | The reset has already committed. The queue retries. If the job is finally dropped, alert as above. | Nobody, except the alert |
| Another device still logged in | Its `sessions` row was deleted. The API checks sessions on every request, so the device is logged out on its next request. | That device is logged out |
| Token leaks through the URL (Referer header, access logs) | Reset pages send `Referrer-Policy: no-referrer`. Query strings stay out of access logs. Single use and the 30-minute window limit the damage. | Nobody |

## Open questions

- Is the queue Postgres-backed? If yes, the "password changed" outbox job commits with the reset. If no, the job must be enqueued after COMMIT. Note: a crash between COMMIT and enqueue loses that email, so the risk is a missing email, not a duplicate one.
- The spec says a new link kills any earlier link immediately. This design kills the old link only when the worker makes the new token. That is normally seconds, but longer if the queue is backed up. Decide whether that is acceptable.
- Two jobs for one account can run at once. Each makes a token and sends an email, and only the last one written works. A user may get a dead link. Decide whether the worker should serialise the upsert per user.
- Breached-password source: a local list (recommended) or the k-anonymity range API.
- Should the request endpoint have a per-IP limit? The spec does not require one.
- What page does a database error show during submit? Not specified.