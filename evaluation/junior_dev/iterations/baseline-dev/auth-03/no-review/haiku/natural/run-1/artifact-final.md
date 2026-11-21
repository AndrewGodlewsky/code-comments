# Design: password reset by emailed link

## Components and data

```
 Browser ──> API server ──> Postgres
                 │            users, sessions, password_resets (new)
                 │
                 └──> email_jobs (queue) ──> email worker ──> mail provider
```

New table `password_resets`:

```
id           uuid pk
user_id      fk users, indexed
token_hash   bytea, unique        SHA-256 of the 32-byte token
issued_at    timestamptz
expires_at   timestamptz          issued_at + 30 min
consumed_at  timestamptz null     set on a successful reset
revoked_at   timestamptz null     set when superseded, or when delivery gives up
```

A row is **live** when `consumed_at IS NULL AND revoked_at IS NULL AND expires_at > now()`.

Notes:
- The raw token is never stored. Lookups hit the unique index on `token_hash`.
- The rate limit counts rows by `issued_at` in the last hour, so no separate counter is needed. Revoked rows still count, so a link that was superseded still used up quota.
- Purge rows about a day after `expires_at`.
- `users`: only `password_hash` changes. `sessions`: all rows for the user are deleted on reset.
- `email_jobs` gets a new job type carrying `reset_id`, the user's address, `not_after` (= `expires_at`) and the raw token encrypted with an app key. The worker needs the token to build the link, so the token sits in the queue briefly. The payload is never logged and the job is deleted once sent. This is the one place the raw token exists outside the link. See open decision 1.

## Request flow: POST /password/forgot { email }

```
REQUEST   POST /password/forgot { email }

  Browser ──> API
                |
                | 1  normalise email (trim, lowercase)
                | 2  BEGIN
                | 3  SELECT user WHERE email = $1 FOR UPDATE
                |        |
                |        +-- no user ---------------------------------+
                |        |                                            |
                |        +-- user found                               |
                | 4  count links issued in last hour                  |
                |        |                                            |
                |        +-- 3 or more --------------------------------+  no writes,
                |        |                                            |  old link kept
                |        +-- fewer than 3                             |
                | 5  revoke live links for user                       |
                | 6  INSERT password_resets (hash, expires +30 min)   |
                | 7  INSERT email_jobs (encrypted token, not_after)   |
                | 8  COMMIT <-----------------------------------------+
                |
                | 9  respond 200 with the generic message (same for every branch)
                v
```

Notes:
- `FOR UPDATE` on the user row serialises concurrent requests, so the count in step 4 cannot race.
- Over the limit, nothing is written. The existing live link is not revoked.
- Unknown addresses and over-limit requests return the same response. The unknown path does one indexed lookup and skips the write, so the timing gap is small. Consider padding it.
- Enqueueing in the same transaction (step 7) means a crash cannot leave a link with no email job.

## Link-click flow: GET /reset?token=T

```
LINK CLICK   GET /reset?token=T

  Browser ──> API
                |
                | hash T with SHA-256
                | SELECT live row WHERE token_hash = hash
                |        |
                |        +-- no live row ---> page: "This link has expired.
                |        |                           Request a new one."
                |        +-- live row
                |              |
                |              +----------> 200 form page
                |                            hidden field carries T
                |                            (no DB write: a GET never burns the link,
                |                             so mail scanners and prefetchers are harmless)
                v
```

Also send `Referrer-Policy: no-referrer` on this page, so the token in the URL does not leak to third-party resources.

## Submit flow: POST /reset { token T, password P }

```
SUBMIT   POST /reset { token T, password P }

  Browser ──> API
                |
                | 1  check T is live (as above)            no  -> expired page
                | 2  check P: 12+ chars, not breached      no  -> form error,
                |                                                 link stays live
                | 3  hash P with argon2id (outside the transaction)
                | 4  BEGIN
                |    SELECT row WHERE token_hash = hash AND live FOR UPDATE
                |        none -> ROLLBACK, expired page
                | 5  UPDATE password_resets SET consumed_at = now()
                | 6  UPDATE users SET password_hash = new hash
                | 7  DELETE FROM sessions WHERE user_id = $u     (every device)
                | 8  INSERT email_jobs (password-changed notice)
                |    COMMIT
                | 9  302 redirect to /login   (no session is created)
                v
```

Notes:
- The token is checked twice: once on page load and again inside the transaction. The `FOR UPDATE` plus the `live` predicate means two concurrent submits cannot both succeed.
- Password rejection happens before the transaction, so the link is not consumed.
- Step 7 covers the current device too. A user who cannot log in may still have a stale cookie, and the sessions table is checked on every request, so deleting the rows takes effect immediately.
- The password-changed notice is enqueued in the same transaction. If the mail fails after that, the reset still stands.

## Email worker

```
EMAIL WORKER

  email_jobs ──> claim job
                   |
                   +-- now > not_after, or reset revoked ---> drop, do not send
                   |
                   +-- send via mail provider
                          |
                          +-- ok ---------------------------> delete job
                          |
                          +-- fail -> retry with backoff (up to 3 times)
                                        |
                                        +-- still failing -> revoke reset row,
                                                             log (no token),
                                                             alert ops, drop job
```

The `not_after` check matters because the 30-minute clock starts at issue, not at send. A job that sat in the queue past expiry should not go out.

## Failure paths

| Case | Behaviour |
|---|---|
| Unknown email | Generic 200. No row, no email. |
| Over 3 links in the rolling hour | Generic 200. No row, no email. Existing live link is kept. |
| Mail provider fails once or twice | Worker retries with backoff. Link stays live. |
| Mail provider gives up after 3 tries | Reset row revoked, failure logged and alerted to ops. The user is not told. They can re-request, which counts against their quota. |
| Email arrives after 30 min | Link shows the expired page. Worker drops the job before sending if it is past `not_after`. |
| Link used a second time | Expired page. The first use already set `consumed_at`. |
| Second request while a link is live | The earlier link is revoked in the same transaction. |
| Two submits race | `FOR UPDATE` plus the `live` predicate. The loser gets the expired page. |
| Weak or breached password | Form error. Link stays live until it expires. |
| Database fails mid-submit | Transaction rolls back. Link not burned, password unchanged. |
| Password-changed email fails | Worker retries. The reset is not reverted. |

## Open decisions

1. **Raw token in the queue.** The worker needs the token to build the link, so it goes into `email_jobs`, encrypted. The alternative is to have the worker generate the token and write its hash, which splits the issue transaction across two systems. I would keep API-side generation and accept the encrypted payload, but this should be reviewed.
2. **Failed sends use quota.** Counting issued rows means a provider outage can lock a user out of re-requests for up to an hour. Counting only delivered mail would be fairer to users but needs delivery feedback from the provider.
3. **Breached-password check.** Either a k-anonymity range lookup against an external breach API or a local list. The first is current; the second avoids a runtime dependency. The brief does not choose.
4. **IP-level rate limiting** on the forgot endpoint is not in the brief. It would guard against spraying many accounts, which the per-account limit does not cover.