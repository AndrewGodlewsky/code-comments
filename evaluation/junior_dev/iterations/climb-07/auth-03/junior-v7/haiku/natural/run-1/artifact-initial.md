# Password reset by emailed link: design

## 1. Request flow: `POST /password/forgot` with `{ email }`

```
 [Web client] --POST /password/forgot {email}--> [API server]
                                                     |
                                    normalise email, look up users.email
                                                     |
                       +------- no such user? ------+
                       |                             |
                       |        BEGIN
                       |        SELECT users WHERE id = ? FOR UPDATE   (per-account lock)
                       |                             |
                       |        count password_reset_tokens
                       |          WHERE user_id = ? AND created_at > now() - 1 hour
                       |                             |
                       |        count >= 3? --------+--> ROLLBACK --------------+
                       |                             |                          |
                       |        UPDATE password_reset_tokens
                       |          SET invalidated_at = now()
                       |          WHERE user_id = ? AND used_at IS NULL
                       |                AND invalidated_at IS NULL
                       |                             |
                       |        INSERT password_reset_tokens
                       |          (user_id, token_hash = sha256(raw), expires_at = now() + 30 min)
                       |                             |
                       |        COMMIT               |
                       |                             |
                       |        enqueue email job { to, raw token }
                       |                             |                          |
                       +-----------------------------+--------------------------+
                                                     |
                         200 OK  "If an account exists for that address,
                                  we've sent a link."
                         (same status and body on every branch)
```

Notes:

- The lock on the `users` row serialises concurrent requests for one account. Without it, two parallel requests can both read a count of 2 and both issue a link, which takes the account past 3 per hour.
- The rate-limit count reads rows that were actually issued. Requests over the limit write nothing, so they cannot invalidate the earlier link.
- The response is sent after the branch is decided, and it is identical on every branch. Nothing in the body, status or headers reveals which branch ran.
- Enqueueing happens after `COMMIT`. If the enqueue itself fails, see failure F4.

## 2. Link-click flow: `GET /password/reset?t=...`, then `POST /password/reset`

```
 [Email link] --> [Web client] --GET /password/reset?t=<token>--> [API server]
                                                                     |
                                              sha256(t) -> lookup password_reset_tokens
                                                                     |
                             valid = row found
                                 AND used_at IS NULL
                                 AND invalidated_at IS NULL
                                 AND expires_at > now()
                                                                     |
                       +------------------ no ----------------------+------------- yes -----+
                       |                                                                     |
          "This link has expired.                                       render "choose a new password"
           Request a new one."                                          form (token goes in the POST body)
          (same page for invalid,
           expired, used, superseded)

 [Form submit] --POST /password/reset {t, new_password}--> [API server]

   BEGIN
   1. sha256(t) -> user_id from password_reset_tokens   (no lock yet)
   2. SELECT users WHERE id = ? FOR UPDATE              (lock the user first)
   3. SELECT password_reset_tokens WHERE token_hash = ? FOR UPDATE
      re-check: used_at, invalidated_at, expires_at    --fail--> expired page, ROLLBACK
   4. check new_password: length >= 12 AND not on breached list
      --fail--> 422 form error, token untouched, link still usable  (ROLLBACK)
   5. UPDATE users SET password_hash = argon2id(new_password)
   6. UPDATE password_reset_tokens SET used_at = now()
   7. DELETE FROM sessions WHERE user_id = ?           (every device, including this one)
   COMMIT
   enqueue "your password was changed" email
   302 redirect to /login, no session created, session cookie cleared
```

Notes:

- The token is checked on page load and again on submit. The load check only decides which page to show. Nothing is burned on load.
- Lock order is always user row first, then token row. The request flow (section 1) also locks the user row first, so a reset and a new request cannot deadlock.
- Step 4 runs before step 5 and does not change the token. A rejected password leaves the link usable until it expires.
- Step 7 is the logout. Sessions are checked on every request, so deleting the rows takes effect immediately. If the system has other long-lived credentials (refresh tokens, API keys) that should also end on password change, revoke them in the same transaction. The spec only mentions sessions.
- A double submit is serialised by the token-row lock. The first commit wins. The second sees `used_at` set and gets the expired page. Only one password change can happen per token.

## 3. Failure paths

| # | Trigger | What the user sees | What happens to state |
|---|---------|--------------------|-----------------------|
| F1 | Unknown email | Generic message | Nothing written, nothing sent |
| F2 | More than 3 issued links in the last hour | Generic message | Nothing written, nothing sent. The earlier unused link stays valid |
| F3 | Mail provider keeps failing | Generic message, and the user is never told the send failed (existing system behaviour) | Worker retries 3 times, then drops the job and logs. On drop, mark that token `invalidated_at` and emit a metric and alert. The user can request again, within the limit |
| F4 | Enqueue fails after `COMMIT` | Generic message, no email arrives | Token exists but is undeliverable. Expires on its own in 30 min. Counts toward the limit. See note below |
| F5 | Link invalid, expired or used at page load | "This link has expired, request a new one" | Nothing changes |
| F6 | Link superseded by a newer request | Same expired page as F5 | Already invalidated by the newer request |
| F7 | New password under 12 characters or breached | 422 form error, user can retry | Token untouched, link valid until expiry |
| F8 | Two submits with the same token at once | One success, one expired page | Row lock; exactly one `used_at` is set |
| F9 | Database error during reset | "Something went wrong, try again" | Transaction rolls back. Password unchanged, token unburned |
| F10 | "Password changed" notice fails to send | Nothing (the reset itself succeeded) | Same retry and drop handling as F3. Log it, but do not roll back the reset |
| F11 | Breached-password service unreachable | Form error asking the user to retry | Use a local copy of the list so there is no runtime dependency. Fail closed if the list cannot be loaded |
| F12 | Token guessing | Nothing | A 256-bit token is not guessable. Still rate-limit both endpoints per IP at the edge |
| F13 | Token leaks through Referer or logs | Nothing | Send `Referrer-Policy: no-referrer` on reset pages. Strip `t` from the address bar after load (`history.replaceState`). Never log query strings for these routes. Put the token in the POST body only |

Notes on F4 and the raw token in the queue:

- The email has to contain the raw token, so the raw token sits in the email job payload until it is sent or dropped. This is a decision for the owner. Options: (a) encrypt the job payload at rest and delete it on completion or drop; (b) write the job in the same transaction as the token row, using a transactional outbox, so a failed enqueue cannot leave a token with no email. Option (b) is cleaner if the queue lives in Postgres. Otherwise do both.
- F3 counts toward the limit. A flaky provider can therefore lock an account out of resets for an hour after 3 failed sends. Counting only delivered mail is the alternative, but it needs delivery callbacks.

## 4. Data

Add one table. Nothing else is stored.

```
password_reset_tokens
  id              bigint  PK
  user_id         bigint  FK users(id) ON DELETE CASCADE, indexed with created_at
  token_hash      char(64)  UNIQUE          -- sha256 of the 32-byte raw token, hex
  created_at      timestamptz
  expires_at      timestamptz               -- created_at + 30 min
  used_at         timestamptz NULL          -- set when the reset succeeds
  invalidated_at  timestamptz NULL          -- set when a newer link supersedes it, or on drop (F3)
```

- The raw token is never stored. It exists only in the email link and the email job payload.
- Purge rows with `created_at` older than 1 hour. That is the length of the rate-limit window. Validity is still enforced by `expires_at`.
- `users.password_hash` is overwritten on success. `sessions` rows for the user are deleted. No other schema change is needed.

## 5. Open decisions

1. Source and refresh schedule for the breached-password list (F11).
2. Whether the rate-limit count should include failed sends (F3).
3. Whether to tell the user when a send is dropped. The current system does not, and this design keeps that behaviour and flags it.
4. Whether to add an outbox table (F4) or rely on the queue's own durability.
5. Whether other credentials (refresh tokens, API keys) must be revoked on reset, beyond sessions.
