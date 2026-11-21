# Password reset by emailed link: design

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

## Flow 1: request a link

`POST /api/password-reset` with body `{email}`.

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

## Flow 2: the link is clicked

The link is `https://<app>/reset#token=<raw>`. The token sits in the URL fragment, so browsers do not send it to servers or in the Referer header.

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

## Flow 3: submit a new password

`POST /api/password-reset/complete` with body `{token, new_password}`.

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

## Data

- **password_reset_tokens** (new): `id`, `user_id` (FK to users), `token_hash` (SHA-256, unique), `created_at`, `expires_at`, `used_at` (nullable), `revoked_at` (nullable). Index on `(user_id, created_at)`.
- **Rate limit:** each row is one issued link, and each issued link is one email. Counting the rows created in the last hour enforces the limit, so no separate table is needed.
- **Retention:** purge rows with `created_at < now() - 1 hour`. Links expire 30 minutes after issue, so older rows are always dead.
- **users:** only `password_hash` changes.
- **sessions:** rows are deleted on a successful reset. The API checks sessions on every request, so deletion takes effect immediately.
- **Clock:** expiry and the rate window use the database clock (`now()`), not app-server clocks.
- **Token:** 256 bits of entropy, so a fast SHA-256 with no salt is enough. The raw token is never stored.

## Coordination

- The `users` row lock serialises link issuance and the rate-limit count for one account.
- The `password_reset_tokens` row lock serialises submissions for one link. A second submit waits, then sees `used_at` set and gets the expired page.
- Issuance racing with submit: whichever transaction commits first wins. The other sees `revoked_at` or `used_at` and fails cleanly.
- Hashing and the breach check run outside the transactions, so no lock is held during slow work.

## Failure paths

| Situation | Behaviour |
|---|---|
| Unknown email | Generic 200. No writes, no job, no email. |
| More than 3 links in the last hour | Generic 200. No link, no email. Existing links stay valid. |
| Email send fails 3 times | Worker logs the job ID (never the link) and drops the job. The user is not told. The link was never delivered and expires in 30 minutes. The user can request again, and that attempt counts toward the limit. |
| Enqueue fails during issuance | Use the same transaction when the queue lives in Postgres, so a failed enqueue rolls back the token and the rate-limit count. If the queue is external, delete the just-inserted row on failure, then return the generic 200. |
| Check or submit with an invalid, expired or used token | Expired page (check) or 410 (submit). The page does not reveal which condition failed. |
| Password too short or breached | 422 with the reason. The link is not burned, so the user can retry until it expires. |
| Breach-list service unavailable | Fail closed. Reject with "please try again." Do not accept an unchecked password. |
| Two submits at once | The row lock lets one through. The other gets the expired page. |
| Database error inside the reset transaction | Full rollback. Nothing changed, the link stays usable, and the user sees a retryable error. |
| "Password changed" email dropped | The password change still stands. The failure is logged. This notice is best-effort. |

## Open decisions and risks

1. **The raw token passes through the email queue.** It has to, because the email contains the link. Treat queue payloads as secrets: restrict access, never log them, and delete the job when it finishes or is dropped.
2. **Silent drop after 3 retries.** Alert on the rate of dropped jobs. Consider telling the user "we could not deliver the email; try again." That would break the fixed generic message, so it needs a product decision.
3. **Timing.** Unknown addresses skip the database writes and the enqueue, so response times differ slightly. If that matters, return the generic response first and do the issuance work asynchronously.
4. **Per-IP rate limits** on the request, check and complete endpoints are not in the brief. Add them to limit abuse. The per-account limit does not cover someone spraying many accounts.
5. **Logging and headers.** Never log raw tokens or passwords. Redact tokens from access logs. Send `Referrer-Policy: no-referrer` on the reset page. Clear the fragment after reading it.
6. **Reload after the fragment is cleared.** The token lives only in memory, so a reload shows the expired page. The user must request a new link. This is a deliberate trade-off against keeping the token in browser history.
