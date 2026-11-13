# Design: Password reset by emailed link

## 1. Parts

```
 Web client --HTTPS--> API server --SQL--> Postgres
                          |                 users, sessions,
                          | add job         password_reset_tokens
                          v
                     Email queue (existing)
                          | claim job
                          v
                     Email worker --send--> Mail provider
                     (3 retries, then log and drop)
```

## 2. Request: POST /password-reset/request {email}

```
Client          API                                    Postgres
  |  {email}      |                                        |
  |-------------->|  1. trim and lower-case the email      |
  |               |  2. BEGIN                              |
  |               |     SELECT user FOR UPDATE ----------->|  locks this account
  |               |  3. no user, or 3 or more tokens       |
  |               |     in the last hour? (count rows) --->|
  |               |     yes: skip to step 5                |
  |               |  4. revoke unused tokens,              |
  |               |     insert new token row,              |
  |               |     add reset email job to queue ----->|
  |               |  5. COMMIT ----------------------------->|
  |<-- 200 "If an account exists for that address, we've sent a link."
```

Notes:
- Every branch returns the same 200 and does not wait for the email. The worker sends it later.
- The token is 32 random bytes from a CSPRNG. Only its SHA-256 hash is stored.
- The rate limit counts issued tokens, so superseded links still use up the 3 per hour. The row lock makes concurrent requests count one after another.
- Normalising uses the same rule as the login lookup, so one address always finds one account.
- The unknown-address branch and the success branch do different amounts of work. We do not add a dummy hash (open question 5).

## 3. Link click

**Valid token** means: the SHA-256 of the token matches a row with `used_at` NULL, `revoked_at` NULL and `expires_at > now()`. Both pages use this test.

### 3a. Page load: GET /reset?t=TOKEN

```
Browser                 API                           Postgres
  | GET /reset?t=TOKEN   |                                |
  |--------------------->|  h = sha256(TOKEN)             |
  |                      |  is the token valid?  -------->|
  |<-- 200 form with hidden token field (valid)           |
  |<-- 200 "this link has expired, request a new one" (not valid)
```

Loading does not consume the token. Reset pages send `Referrer-Policy: no-referrer`.

### 3b. Submit: POST /reset {token, new_password}

```
Browser                 API                           Postgres
  | {token, password}    |                                |
  |--------------------->|  1. valid token? no: expired page
  |                      |  2. password 12+ characters and not
  |                      |     on breached list? no: 422 form again,
  |                      |     token untouched
  |                      |  3. hash password (argon2id)   |
  |                      |  4. BEGIN                      |
  |                      |     SELECT token FOR UPDATE -->|  locks token row
  |                      |     valid token now? no: ROLLBACK, expired page
  |                      |  5. UPDATE users password_hash>|
  |                      |     set token used_at = now()  |
  |                      |     revoke other tokens of user|
  |                      |     DELETE sessions of user -->|
  |                      |     add "password changed" job |
  |                      |  6. COMMIT ------------------->|
  |<-- 303 Location: /login  (no session cookie)          |
```

Notes:
- The typed password lives only in memory. It is never stored or logged, and it is dropped when the expired page is shown.
- Hashing runs before BEGIN, so the lock covers only the writes. The check under the lock stops a double submit from applying twice.
- The "password changed" job is written in the same transaction, so it exists only if the reset committed. Where the queue lives is open question 3.
- Nobody is logged in. The link proves control of the email. The user then logs in with the new password.

## 4. Failure paths

| Case | Behaviour | Stored state |
|---|---|---|
| Unknown email, or over 3 per hour | Generic 200, nothing sent | Nothing written |
| Newer link issued | Older link revoked. Its queued job is skipped by the worker (section 6). | Old row revoked |
| Send fails 3 times, or provider outage | Job dropped. No email, no notice to the user. Token expires unused. Each new request uses a slot. | Token unused until expiry |
| Link expired, used or revoked | Expired page on load and on submit | Unchanged |
| Weak or breached password | 422, form again. Link works until expiry. | Nothing changed |
| Double submit or race | Row lock. The second submit sees a used token and gets the expired page. | One reset applies |
| DB error mid-transaction | Rollback | Password, token and sessions unchanged |

## 5. Data

- `password_reset_tokens`: `id` (uuid, pk), `user_id` (fk), `token_hash` (bytea 32, unique), `created_at`, `expires_at` (created_at + 30 min), `used_at` (nullable), `revoked_at` (nullable). Index on `(user_id, created_at)` for the rate limit.
- `users`: only `password_hash` changes. `sessions`: schema unchanged. A reset deletes all rows for the user.
- Email job, one of two kinds. It is deleted when sent or dropped. Logs never contain the token or the link.
  - `{kind: "reset", token_id, user_id, token_ciphertext}`. The ciphertext is the raw token encrypted with an application key.
  - `{kind: "password_changed", user_id}`. It carries no token.
- Purge: an hourly scheduled delete (a cron job if the API has no scheduler) removes token rows older than 24 h. That is well past the 30-minute link life and the 1-hour rate window. Jobs are sent long before 24 h, so the purge never removes a row a job still needs. A link clicked after its row is purged shows the expired page.
- SHA-256 is enough for the hash, because the token carries 256 random bits.
- The encrypted token stays in the job because minting the token in the worker would move the token row, the revoke and the rate-limit count out of the request transaction.

## 6. Link and worker

- Token: 43-character base64url encoding of the 32 bytes. Link: `{PUBLIC_BASE_URL}/reset?t=<token>`, where `PUBLIC_BASE_URL` is configuration. The form posts the token as a hidden field. No query string is logged.
- For a `reset` job, the worker:
  1. Reads the token row by `token_id`.
  2. If the row is missing, revoked, used or expired, it skips the job and deletes it. No send, no retry. This is the superseded check.
  3. Otherwise it decrypts `token_ciphertext`, builds the link and sends the email.
- For a `password_changed` job, the worker reads the account's email address from `users` by `user_id` and sends the "your password was changed" email. There is no superseded check, because there is no token.
- A send error on either kind is retried up to 3 times with backoff, then logged and dropped. A skip is not a send error and is not retried.
- If the worker crashes after sending and before deleting the job, the job may be sent again. A repeated reset email carries the same single-use link, so security holds. We accept the duplicate (open question 7).

## 7. Open questions

1. Failed sends and quota: should a dropped reset email free its slot? The quota currently counts it.
2. Breached-password source: a hosted k-anonymity range API or a local list. Pick one and state its refresh rule.
3. Queue location: if the queue is outside Postgres, the "password changed" notice needs enqueue-after-commit. A crash between commit and enqueue loses it.
4. Session cache: the brief describes none. If the API caches sessions, the cache must be invalidated on delete.
5. Timing gap: the unknown-address branch writes nothing and the success branch writes two rows. Accepted for now.
6. Per-IP rate limit: left out to keep scope.
7. Queue claim rule: the brief names the existing queue but not how it hands out a job after a crash (lease or visibility timeout). Until this is known, a crash after send may cause a second send. Section 6 accepts that.