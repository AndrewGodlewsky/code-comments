# Password reset by emailed link: design

## Summary

Users who cannot log in can ask for a reset link. If the account exists and is under its limit, the API saves a hash of a one-time token and queues an email with a link that contains the raw token. The link opens a form. A valid new password replaces the old one, deletes every session and burns the link.

Today the web client calls the API server, which reads and writes Postgres (`users`, `sessions`). Outgoing email goes into an email queue. A worker sends it through the mail provider and retries 3 times with backoff. After that it logs the failure and drops the job, and nobody is told.

## Terms

- **Raw token**: 32 random bytes. It appears only inside the link in the email.
- **Token hash**: SHA-256 of the raw token. This is the only form stored in the database.
- **Link**: `https://<app>/reset#token=<raw>`. It works once and expires 30 minutes after it is issued.
- **Issue**: create a new link row and queue its email.
- **Revoke**: mark an older unused link as dead. It can no longer be used.
- **Burn**: mark a link as used. It can no longer be used.
- **Queue job**: an email waiting for the email worker.

## Components

```
+-----------+   HTTPS    +-----------+    SQL    +--------------------------------+
| Web       |----------->| API       |---------->| Postgres                       |
| client    |            | server    |           |   users                        |
+-----------+            +-----+-----+           |   sessions                     |
                               |                 |   password_reset_tokens (new)  |
                               | enqueue         +--------------------------------+
                               v
                         +-----------+   job    +-----------+   HTTPS   +-----------+
                         | Email     |--------->| Email     |---------->| Mail      |
                         | queue     |          | worker    |           | provider  |
                         +-----------+          +-----+-----+           +-----------+
                                                      |
                                                      | 3 retries with backoff,
                                                      | then log and drop the job
                                                      v
                                                   (no notice to user)
```

The raw token must pass through the queue, because the email contains the link. Treat queue payloads as secrets (see Secrets and logs).

## Flows

### Flow 1: request a link

Starts when the user submits their email: `POST /api/password-reset` with `{email}`.

```
 Client            API                                          Postgres / queue
   |                 |
   |--- email ------>|  trim and lowercase the email
   |                 |  SELECT user WHERE email = $1
   |                 |
   |                 |  [no such user] --------------------->  no writes, no job
   |                 |
   |                 |  [user found]  BEGIN
   |                 |    SELECT users WHERE id = $1 FOR UPDATE
   |                 |        (serialises concurrent requests for one account)
   |                 |    n = COUNT password_reset_tokens
   |                 |          WHERE user_id = $1 AND created_at > now() - 1 hour
   |                 |    if n >= 3:
   |                 |        ROLLBACK. No link, no email. Existing links untouched.
   |                 |    else:
   |                 |        UPDATE password_reset_tokens SET revoked_at = now()
   |                 |          WHERE user_id = $1 AND used_at IS NULL
   |                 |                AND revoked_at IS NULL
   |                 |        raw = 32 bytes from a CSPRNG
   |                 |        INSERT password_reset_tokens (user_id,
   |                 |               token_hash = SHA-256(raw),
   |                 |               expires_at = now() + 30 minutes)
   |                 |        INSERT queue job {to, link containing raw} ---> queue
   |                 |    COMMIT
   |                 |
   |<-- 200 "If an account exists for that address, we've sent a link."
   |                 |  Identical response on every branch.
```

Steps:

1. Trim and lowercase the email, then look up the user. If there is no user, go to step 6. No writes happen.
2. Start a transaction and lock the user row (`FOR UPDATE`). Concurrent requests for the same account wait here.
3. Count this user's links created in the last hour. If there are 3 or more, roll back. No link and no email. Existing links stay valid.
4. Otherwise, revoke every unused, unrevoked link for this user. The new link replaces them.
5. Make a raw token from 32 secure random bytes. Insert a row with its SHA-256 hash and an expiry of now + 30 minutes. Insert the email job with the link. Commit.
6. Return the generic message: "If an account exists for that address, we've sent a link." Every branch returns this.

### Flow 2: the link is clicked

Starts when the user opens the link. The token sits in the URL fragment, so the browser does not send it to the server or in the Referer header.

```
 Browser          Web client                              API
   |                 |
   |-- open link --->|  read token from location.hash
   |                 |  clear the fragment (history.replaceState)
   |                 |  POST /api/password-reset/check  {token}
   |                 |----------------------------------->|  h = SHA-256(token)
   |                 |                                    |  SELECT row WHERE token_hash = h
   |                 |                                    |    AND used_at IS NULL
   |                 |                                    |    AND revoked_at IS NULL
   |                 |                                    |    AND expires_at > now()
   |                 |<-----------------------------------|  200 {valid: true | false}
   |                 |
   |  valid:   show "choose a new password" form (token kept in memory)
   |  invalid: show "This link has expired. Request a new one."
```

Steps:

1. The web client reads the token from the fragment and clears the fragment. The token is now held only in memory.
2. The client sends the token to `POST /api/password-reset/check`. The API reads only.
3. The API hashes the token and checks for an unused, unrevoked, unexpired row (database clock).
4. Valid: show the form. Invalid: show the expired page. The page does not say which check failed.

A reload after step 1 loses the token, so the user sees the expired page and must request a new link. This is a deliberate trade-off to keep the token out of browser history.

### Flow 3: submit a new password

Starts when the user submits the form: `POST /api/password-reset/complete` with `{token, new_password}`.

```
 Client          API                                             Postgres / queue
   |                |
   |-- submit ----->|  1. h = SHA-256(token); look up the row (no lock)
   |                |     not found, used, revoked or expired:
   |<-- 410 ------- |        show the "expired, request a new one" page
   |                |
   |                |  2. Policy check: length >= 12, not on the breached list
   |                |     rejected:
   |<-- 422 --------|        show the reason; form stays up; link NOT touched
   |                |
   |                |  3. hash = argon2id(new_password)
   |                |     (outside the transaction, so no row lock is held)
   |                |
   |                |  4. BEGIN
   |                |       SELECT row WHERE token_hash = h FOR UPDATE
   |                |           (serialises double submits)
   |                |       if not found, used, revoked or expired:
   |                |           ROLLBACK, 410 as above
   |                |       UPDATE users SET password_hash = hash
   |                |           WHERE id = row.user_id
   |                |       UPDATE password_reset_tokens SET used_at = now()
   |                |           WHERE id = row.id
   |                |       DELETE FROM sessions WHERE user_id = row.user_id
   |                |           (every device, including this one)
   |                |       INSERT queue job "your password was changed" ---> queue
   |                |     COMMIT
   |                |
   |<-- 200, redirect to /login
   |                |  No session cookie is set. The user is not logged in.
```

Steps:

1. Hash the token and look up the row without a lock. If it is not found, used, revoked or expired, return 410 and show the expired page.
2. Check the password: at least 12 characters, and not on the breached-password list. If it fails, return 422 with the reason. The link is not burned, so the user can retry until it expires. If the breach service is unavailable, reject with "please try again." Never accept an unchecked password.
3. Hash the password with argon2id. This runs outside the transaction, so no lock is held during the slow work.
4. Start a transaction and lock the token row (`FOR UPDATE`). Check the row again. If it is no longer usable, roll back and return 410. A second submit waits here, then fails.
5. Store the new password hash on the user. Mark the link used. Delete all of the user's sessions, including this device. Queue the "your password was changed" email. Commit.
6. Return 200 and redirect to `/login`. Set no session cookie. The user is not logged in.

## What happens when things fail

| Situation | What happens |
|---|---|
| Unknown email | Generic 200. No writes, no job, no email. |
| 3 or more links in the last hour | Generic 200. No link, no email. Existing links stay valid. |
| Email send fails 3 times | The worker logs the job ID (never the link) and drops the job. The user is not told. The link was never delivered and expires in 30 minutes. A new request counts toward the limit. |
| Enqueue fails during issue | If the queue is in Postgres, the same transaction rolls back the link and the count. If the queue is external, delete the row just inserted, then return the generic 200. Which case applies is open question 1. |
| Invalid, expired or used token at check | Show the expired page. It does not say why. |
| Invalid, expired or used token at submit | Return 410 and show the expired page. |
| Password too short or breached | Return 422 with the reason. The link is not burned. |
| Breach service unavailable | Reject with "please try again." Never accept an unchecked password. |
| Two submits at once | The row lock lets one through. The other sees the link used and gets the expired page. |
| Database error during reset | Full rollback. Nothing changed. The link stays usable. The user sees a retryable error. |
| "Password changed" email dropped | The password change stands. The failure is logged. This notice is best-effort. |

## Stored data

- **`password_reset_tokens`** (new): `id`, `user_id` (FK to users), `token_hash` (SHA-256, unique), `created_at`, `expires_at`, `used_at` (nullable), `revoked_at` (nullable). Index on `(user_id, created_at)`.
- **Rate limit**: count this user's rows created in the last hour. Each row is one link and one email, so no other table is needed.
- **Cleanup**: delete rows created more than 1 hour ago. Links expire 30 minutes after issue, so these rows are always dead.
- **`users`**: only `password_hash` changes.
- **`sessions`**: this user's rows are deleted on a successful reset. The API checks sessions on every request, so the logout takes effect at once.
- **Clock**: expiry and the rate window use the database clock (`now()`), not app-server clocks.
- **Hashing the token**: the token has 256 bits of randomness, so a fast SHA-256 with no salt is enough. The raw token is never stored.

## Secrets and logs

- Never log raw tokens or passwords. Redact tokens from access logs.
- Restrict access to the queue. Delete each job when it finishes or is dropped.
- The reset page sends `Referrer-Policy: no-referrer`.
- The client clears the fragment after reading it (Flow 2, step 1).

## Open questions

1. Where does the email queue live? If it is in Postgres, a failed enqueue rolls back with the transaction. If it is external, the cleanup-on-failure rule applies. The brief does not say.
2. Should users be told when an email is dropped? That would break the fixed generic message, so it needs a product decision. Until then, alert on the rate of dropped jobs.
3. Responses for unknown addresses are faster, because they skip the writes and the enqueue. Is that acceptable? If not, respond first and issue the link in the background.
4. Per-IP rate limits on the request, check and complete endpoints are not in the brief. The per-account limit does not stop one client trying many accounts.