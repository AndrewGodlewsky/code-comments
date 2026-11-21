# Design: password reset by emailed link

## Scope

"Forgot password?" for the consumer app. A user who cannot log in enters their email address and receives a one-time link to set a new password. This covers the request flow, the link-click flow, and the failure paths.

## Data

Only one new table is needed. `users` and `sessions` are unchanged, except that a successful reset deletes the user's `sessions` rows.

```
password_reset_tokens
  id             bigint        PK
  user_id        bigint        FK users(id) ON DELETE CASCADE
  token_hash     bytea         UNIQUE NOT NULL   -- SHA-256 of the raw 32-byte token
  issued_at      timestamptz   NOT NULL DEFAULT now()
  expires_at     timestamptz   NOT NULL          -- issued_at + 30 minutes
  consumed_at    timestamptz   NULL              -- set when the password is changed
  superseded_at  timestamptz   NULL              -- set when a newer link is issued
  INDEX (user_id, issued_at)

-- A token is ACTIVE when:
--   consumed_at IS NULL AND superseded_at IS NULL AND expires_at > now()
```

Notes:

- The raw token exists only in the email link. The database holds `token_hash` only.
- Rows are kept after they are used or superseded, because the rate limit counts them. Purge rows older than 24 hours with a scheduled job.
- All expiry checks use the database clock (`now()`), not the application clock.
- The `email job` payload for the reset email carries the link, so it carries the raw token. Treat the queue table as holding secrets: do not log job payloads, restrict access, and delete the job row once it is sent or dropped.

## Request flow: POST /password/forgot

```
                         POST /password/forgot { email }
                                      |
                                      v
                      +-------------------------------+
                      | normalize email, look up user |
                      +-------------------------------+
                           | no user              | user found
                           v                      v
                  return generic message     BEGIN transaction
                  (nothing written,          SELECT users WHERE id = $1 FOR UPDATE
                   nothing sent)                 |   (serializes requests per account)
                                                 v
                                      count tokens issued in last hour:
                                      SELECT count(*) FROM password_reset_tokens
                                       WHERE user_id = $1 AND issued_at > now() - 1h
                                                 |
                                 count >= 3  ----+---- count < 3
                                     |                      |
                                     v                      v
                          COMMIT, return generic    UPDATE password_reset_tokens
                          (no token, no email)         SET superseded_at = now()
                                                       WHERE user_id = $1
                                                         AND consumed_at IS NULL
                                                         AND superseded_at IS NULL
                                                             |
                                                             v
                                                    token = random 32 bytes
                                                    INSERT password_reset_tokens
                                                      (token_hash, expires_at = now() + 30m)
                                                    INSERT email job
                                                      { type: password_reset,
                                                        token_id, link(token) }
                                                             |
                                                             v
                                                    COMMIT, return generic message
                                                             |
                                                             v  (asynchronous)
                                        email worker -> mail provider
                                        retry up to 3 times with backoff
                                        final failure: log, mark token superseded,
                                                       drop job
```

Notes:

- The response is the same string in every branch: "If an account exists for that address, we've sent a link."
- Unknown addresses do no writes and enqueue nothing. Keep the code path before the response short and similar in both branches, so response time does not reveal whether an account exists.
- The email job is inserted in the same transaction as the token row. A job exists only if its token exists and has committed.
- The `FOR UPDATE` lock on the user row prevents two concurrent requests from both passing the rate limit and both issuing links.
- A request over the limit creates no token and no job, but still returns the generic message.
- Issuing a new link supersedes older unused links in the same transaction, so there is never more than one active link per account.

## Link-click flow: GET page load, POST submit

```
 GET /password/reset?token=T                     POST /password/reset { token, password }
            |                                                  |
            v                                                  v
  hash = SHA-256(T)                                  hash = SHA-256(token)
  row ACTIVE for hash?                               row ACTIVE for hash?
     | no                 | yes                         | no -----------------> "link has expired,
     v                    v                             |                       request a new one"
  "link has expired"   render form                      | yes                     page
  page                 (token in hidden field)          v
  (token NOT consumed)                              password >= 12 chars AND
                                                    not on breached list?
                                                         | no ------------------> re-render form with error
                                                         |                       (token NOT consumed,
                                                         | yes                    link still usable)
                                                         v
                                                BEGIN transaction
                                                SELECT token row FOR UPDATE
                                                recheck ACTIVE
                                                   | no -> ROLLBACK, expired page
                                                   | yes
                                                   v
                                                UPDATE users SET password_hash = new
                                                UPDATE password_reset_tokens
                                                   SET consumed_at = now()
                                                       WHERE id = token_id
                                                DELETE FROM sessions WHERE user_id = $1
                                                INSERT email job { type: password_changed,
                                                                   user_id }
                                                COMMIT
                                                         |
                                                         v
                                                clear session cookie on this response,
                                                redirect 303 to /login
                                                (no automatic login)
```

Notes:

- GET never consumes the token. Email link scanners and prefetchers can open the URL without using it up.
- The POST checks the token before the password policy, so a rejected password leaves the link active. The token is checked again inside the transaction, under a row lock, so a double submit or race cannot consume the token twice.
- The password hash update, the token burn, and the session deletion all commit together. If any step fails, nothing changes and the link stays usable until it expires.
- The "password changed" email is enqueued inside the same transaction, so it is sent only if the reset committed.
- Set `Referrer-Policy: no-referrer` on the reset page, so the token in the URL does not leak to third-party resources. Do not log full reset URLs.
- The breached-password check runs before the transaction and holds no lock. If the breached-list service is unavailable, reject the password with a retry message. Do not accept it, and do not consume the link.

## Failure paths

| Situation | Result | Link state | Email sent |
|---|---|---|---|
| Unknown email | Generic message | None created | No |
| Over 3 emails in the rolling hour | Generic message | No new link; existing active link stays active | No |
| Email send fails 3 times | Worker logs and drops the job. User is not told | Token row stays active until expiry unless the worker marks it superseded | No |
| Second request while a link is active | New link issued; old one superseded | Old link now expired | Yes (new) |
| GET with invalid, expired, used or superseded token | "Link has expired" page | Unchanged | No |
| POST with token that became invalid after GET | "Link has expired" page, no password change | Unchanged | No |
| POST with password under 12 characters or breached | Form re-shown with error | Still active | No |
| Double submit or race on the same valid token | First commits. Second fails the row-lock recheck and sees the expired page | Consumed once | Change email sent once |
| Transaction fails during reset | Rollback. Error page or form re-shown | Still active | No |
| Password-changed email fails | Worker retries. Reset already committed; user still logged out and redirected | Consumed | Retried by worker |
| Old session used after reset | Rejected on next request, since its `sessions` row is gone | n/a | n/a |

## Known gaps and decisions for review

- **Silent drop after 3 failed sends.** The spec says nobody is notified. Two mitigations are included: the worker marks the token superseded when it drops a reset job, and it emits a counted alert. Without the first, a dead link stays active for up to 30 minutes. Without the second, the failure rate is invisible.
- **Rate limit counts undelivered emails.** A link that never arrives still uses one of the 3 hourly slots. This is consistent with the rule "at most 3 reset emails in any rolling hour," which counts issuance.
- **Raw token in the queue.** It is needed for the email. The mitigation is restricted access, no logging of payloads, and deleting job rows promptly.
- **Rate limit on the forgot endpoint by IP or address.** Not specified. The per-account limit caps email volume but does not stop someone from making many requests. An endpoint-level limit can be added separately if needed.
- **Session deletion vs. in-flight requests.** A request already past the session check when the reset commits may complete. This window is milliseconds and is accepted.
