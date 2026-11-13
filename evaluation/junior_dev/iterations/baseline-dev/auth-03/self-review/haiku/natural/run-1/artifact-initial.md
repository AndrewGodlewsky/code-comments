# Password reset by emailed link: design

## 1. Request flow: `POST /password-reset { email }`

```
 Browser            API server                       Postgres                 Email queue / worker      Mail provider
    |                   |                                |                              |                       |
    |-- email --------->|                                |                              |                       |
    |                   |-- 1. SELECT user by email ---->|                              |                       |
    |                   |<-- none? -> respond generic ---|  (stop: nothing written,     |                       |
    |                   |                                |   nothing sent)              |                       |
    |                   |-- 2. BEGIN                     |                              |                       |
    |                   |-- 3. SELECT users WHERE id=?   |                              |                       |
    |                   |      FOR UPDATE -------------->|  (serializes concurrent      |                       |
    |                   |                                |   requests for this account) |                       |
    |                   |-- 4. COUNT password_reset_     |                              |                       |
    |                   |      tokens WHERE user_id=?    |                              |                       |
    |                   |      AND created_at > now()-1h |                              |                       |
    |                   |   count >= 3 -> COMMIT, respond generic (stop: no new link,  |                       |
    |                   |                 no email, existing link stays live)          |                       |
    |                   |-- 5. UPDATE tokens SET         |                              |                       |
    |                   |      invalidated_at = now()    |                              |                       |
    |                   |      WHERE user_id=? AND used_at IS NULL                     |                       |
    |                   |        AND invalidated_at IS NULL                            |                       |
    |                   |-- 6. INSERT token row          |                              |                       |
    |                   |      (token_hash, expires_at   |                              |                       |
    |                   |       = now()+30 min)          |                              |                       |
    |                   |-- 7. COMMIT ------------------>|                              |                       |
    |                   |-- 8. enqueue job {user_id, token_id, link} ----------------->|                       |
    |<-- generic msg ---|    (respond after 7/8, padded to a fixed floor)              |                       |
    |                   |                                |                 9. send ---->|-- email ------------->|
    |                   |                                |                 retry x3,    |   link:               |
    |                   |                                |                 backoff      |   /reset?token=<T>    |
    |                   |                                |                 final fail:  |                       |
    |                   |                                |<-- mark token invalidated,   |                       |
    |                   |                                |    log + alert, drop job     |                       |
```

Notes:
- The response text and status are identical on every branch. Unknown addresses do no writes and enqueue nothing. Pad response time to a fixed floor so the branches look alike.
- Rate limit: the row lock in step 3 makes the count in step 4 exact under concurrency. Rows are counted whether or not their email later succeeds.
- Step 5 runs only after the limit check passes, so a rate-limited request never kills the earlier link.
- Step 8 runs after commit. If the enqueue fails, mark the new token invalidated, log it, and still return the generic message. If the queue lives in Postgres, put the enqueue in step 7's transaction instead.

## 2. Link-click flow: `GET /reset?token=T` then `POST /reset`

```
 Browser                      API server                              Postgres
    |                             |                                       |
    |-- GET /reset?token=T ------>|  h = SHA-256(T)                       |
    |                             |-- SELECT id FROM password_reset_tokens|
    |                             |   WHERE token_hash = h                |
    |                             |     AND used_at IS NULL               |
    |                             |     AND invalidated_at IS NULL        |
    |                             |     AND expires_at > now() ---------->|
    |                             |<-- row / none ------------------------|  (GET writes nothing)
    |<-- form (T in hidden field) |   row found                           |
    |<-- "this link has expired,  |   none found                          |
    |     request a new one"      |                                       |
    |                             |                                       |
    |-- POST /reset {T, pw} ----->|  1. re-check token (same WHERE)       |
    |                             |     none -> expired page, stop        |
    |                             |  2. check pw: >= 12 chars, not        |
    |                             |     breached (local list, no DB)      |
    |                             |     rejected -> form error, stop      |
    |                             |     (link untouched, still valid)     |
    |                             |  3. hash pw (argon2/bcrypt)           |
    |                             |  4. BEGIN                             |
    |                             |  5. SELECT token FOR UPDATE, re-check |
    |                             |     none -> ROLLBACK, expired page    |
    |                             |  6. UPDATE users SET password_hash    |
    |                             |  7. UPDATE tokens SET used_at = now() |
    |                             |  8. DELETE FROM sessions WHERE        |
    |                             |     user_id = ?  (all devices)        |
    |                             |  9. COMMIT ------------------------->|
    |                             |  10. enqueue "password changed" email |
    |<-- 303 redirect /login -----|      (no session is created)          |
```

Notes:
- The GET path only reads. Email link scanners that prefetch the URL cannot burn the link.
- The POST re-checks the token twice: once before the expensive work, and again under `FOR UPDATE` in the transaction. Two concurrent submits of the same link therefore leave one success and one expired page.
- Steps 6 to 8 share one transaction, so the password, the burned link and the session deletion succeed or fail together.
- Step 10 runs after commit. If it fails, the reset still stands, the queue retries it, and the failure is logged.
- The token travels in the URL only on the GET. Send `Referrer-Policy: no-referrer` on the reset page, keep the raw token out of access logs where the stack allows, and carry it in the POST body.

## 3. Data

Only one new table. The rate limit reuses it, and no other table stores tokens.

```
password_reset_tokens
  id              bigserial    pk
  user_id         bigint       not null  references users(id) on delete cascade
  token_hash      bytea        not null  unique      -- SHA-256 of the 32-byte raw token
  created_at      timestamptz  not null  default now()
  expires_at      timestamptz  not null             -- created_at + 30 min
  used_at         timestamptz                       -- set by a successful reset
  invalidated_at  timestamptz                       -- set when a newer link replaces it, or the send fails or enqueue fails
  index (user_id, created_at)

users:      password_hash replaced on success (no other change)
sessions:   rows for the account deleted on success (no other change)
```

- Retention: purge rows with `created_at < now() - 1 hour`. That is the longest the rate-limit window needs them.
- Raw token: 32 bytes from a CSPRNG, base64url-encoded (43 characters) in the link. It is never stored in Postgres or logged.
- The email job payload carries the link, so the raw token sits in the queue until the send completes or is dropped. Keep payloads short-lived and restrict queue access.
- Config: TTL 30 min, cap 3 per rolling hour, minimum password length 12.

## 4. Failure paths

1. **Unknown email:** generic message, no write, no email.
2. **Over the hourly cap:** generic message, no write, no email. The earlier link stays live.
3. **Enqueue fails:** invalidate the new token, log, still return generic.
4. **Mail send fails three times:** the worker logs, invalidates the token, raises an alert, and drops the job. The user sees nothing. Failed sends still count toward the cap, so a user can be blocked for up to an hour after three failures. That is the conservative default, and it is an open decision.
5. **Link expired, used or invalidated on load:** expired page, no write.
6. **Link submitted after expiry or after use:** expired page, rolled back, nothing changed.
7. **Password too short or breached:** form error, no write, link still usable until it expires.
8. **Breached-list lookup unavailable:** reject with "try again later". Fail closed, so no unchecked password is accepted.
9. **Database error during the reset transaction:** roll back. The link stays usable.
10. **Password-changed email fails:** the reset stands, the queue retries, and the failure is logged.
11. **Two submits of one link:** the first succeeds. The second, under the row lock, sees the link burned and gets the expired page.
12. **Two requests for one account at once:** the row lock serializes them, so the cap holds.

## 5. Open decisions

- Whether failed sends should count toward the cap (see failure path 4). The default counts every issued link.
- Whether the enqueue sits in the same transaction as the token insert (outbox pattern). This depends on whether the queue is in Postgres.
- The generic message says "we've sent a link" even when the send later fails. The brief fixes that wording, so monitor drop rates and alert on them.
- Logs record `user_id` and `token_id` only. Never the raw token, the link or the password.