# Design: password reset by emailed link

## Summary

A user who cannot log in enters their email on 'Forgot password?'. The API stores a hash of a one-time token that expires after 30 minutes, then queues an email whose link carries the raw token. Opening the link shows a form. A valid submit with an acceptable password replaces the password hash, burns the token, deletes all of the user's sessions and queues a confirmation email. The forgot endpoint always gives the same answer, so it does not reveal which addresses have accounts.

## Terms

- **Token**: 32 random bytes, sent only inside the emailed link. The database stores only its SHA-256 hash, `token_hash`.
- **Active link**: a token that is not consumed, not superseded and not expired. Expiry uses the database clock, `now()`.
- **Consumed**: the token was used for a successful password change.
- **Superseded**: a newer link was issued for the account, or the email could not be delivered.
- **Email job**: a row in the email queue, inserted by the API and sent by the email worker. A reset job holds the raw token in its link.
- **Rolling hour**: the last 60 minutes, counted from `issued_at`.

## Data

One new table. A successful reset changes `users.password_hash` and deletes that user's `sessions` rows. Nothing else changes.

```
password_reset_tokens
  id             bigint        PK
  user_id        bigint        FK users(id) ON DELETE CASCADE
  token_hash     bytea         UNIQUE NOT NULL   -- SHA-256 of the raw 32-byte token
  issued_at      timestamptz   NOT NULL DEFAULT now()
  expires_at     timestamptz   NOT NULL          -- issued_at + 30 minutes
  consumed_at    timestamptz   NULL              -- set when the password is changed
  superseded_at  timestamptz   NULL              -- set when a newer link is issued, or delivery fails
  INDEX (user_id, issued_at)

-- ACTIVE when: consumed_at IS NULL AND superseded_at IS NULL AND expires_at > now()
```

Rows stay after they are consumed or superseded, because the hourly limit counts them. A scheduled job deletes rows older than 24 hours.

The email queue holds secrets. Never log job payloads, restrict who can read the queue, and delete a job row once it is sent or dropped.

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

Steps:

1. Normalize the email: trim spaces and lowercase it. Look it up in `users.email`.
2. Unknown address: return the generic message. Write nothing and queue nothing.
3. Known address: open a transaction and lock the user row with `SELECT ... FOR UPDATE`. This makes requests for one account run one at a time, so two requests cannot both pass the limit.
4. Count the tokens issued in the rolling hour. If there are 3 or more, commit and return the generic message. Nothing is created or sent. Consumed and superseded links still count.
5. Otherwise, in the same transaction: supersede every older unused link, insert the new token with `expires_at = now() + 30 minutes`, and insert the email job that holds the link. A job therefore exists only if its token committed, and there is never more than one active link. This guarantee needs the queue to live in Postgres (see Open questions).
6. Commit and return the generic message. The email worker sends the email later.

Every branch returns the same message: 'If an account exists for that address, we've sent a link.' Both branches take a short path before responding, so response time does not reveal whether an account exists.

## Link-click flow: GET page load, POST submit

```
 GET /password/reset?token=T                     POST /password/reset { token, password }
            |                                                  |
            v                                                  v
  hash = SHA-256(T)                                  hash = SHA-256(token)
  row ACTIVE for hash?                               row ACTIVE for hash?
     | no               | yes                          | no ---------------> 'link has expired,
     v                  v                              |                     request a new one' page
  'link has expired'   render form                     | yes
  page                 (token in hidden field)         v
                                                  password >= 12 chars AND
                                                  not on breached list?
                                                       | no ----------------> re-render form with error
                                                       |                     (link stays active)
                                                       | yes
                                                       v
                                                BEGIN transaction
                                                SELECT token row FOR UPDATE
                                                recheck ACTIVE
                                                   | no -> ROLLBACK, expired page
                                                   | yes
                                                   v
                                                UPDATE users SET password_hash = new
                                                UPDATE password_reset_tokens SET consumed_at = now()
                                                DELETE FROM sessions WHERE user_id = $1
                                                INSERT email job { type: password_changed, user_id }
                                                COMMIT
                                                   |
                                                   v
                                                clear session cookie on this response,
                                                redirect 303 to /login (no automatic login)
```

Steps:

1. The link is `https://<app-origin>/password/reset?token=<token>`. The token is base64url with no padding, 43 characters. The form page keeps it in a hidden field and sends it back on POST.
2. GET only checks the token. It never consumes it, so link scanners and prefetchers cannot use it up.
3. On POST, check the token first. If it is not active, show the expired page.
4. Then check the password: at least 12 characters and not on the breached list. The check runs before the transaction, with no lock held. The plain password is never sent to a third party. If the password fails, re-show the form with an error. The link stays usable until it expires.
5. In one transaction, lock the token row with `FOR UPDATE` and recheck that it is active. A double submit therefore consumes the token only once. Then update the password hash, set `consumed_at`, delete all of the user's `sessions` rows and insert the 'password changed' email job. Everything commits together, or nothing changes.
6. Clear the session cookie on this response, then redirect 303 to /login. Do not log the user in.

Notes:

- The API checks a `sessions` row on every request, so deleting the user's rows logs out every device. If the browser that submitted had no session cookie, there is nothing to clear.
- The reset page sends `Referrer-Policy: no-referrer`. Never log full reset URLs.

## Failure paths

| Situation | Result | Link state | Email sent |
|---|---|---|---|
| Unknown email | Generic message | None created | No |
| Over 3 links in the rolling hour | Generic message | No new link; the active link stays active | No |
| Second request while a link is active | New link issued; old one superseded | Old link dead | Yes (new) |
| Reset email fails 3 times | Worker logs, marks the token superseded, drops the job. The user is not told; a counted alert is emitted (destination open, see Open questions) | Dead; still counts toward the hourly limit | No |
| GET with an invalid, expired, used or superseded token | 'Link has expired' page | Unchanged | No |
| POST with a token that is no longer active | 'Link has expired' page, no password change | Unchanged | No |
| POST with a password under 12 characters, or on the breached list | Form re-shown with error | Still active | No |
| Breached list unavailable | Form re-shown with 'try again' | Still active | No |
| Double submit, or race on the same valid token | First commits. Second fails the row-lock recheck and sees the expired page | Consumed once | One change email |
| Transaction fails during reset | Rollback. Error page or form re-shown | Still active | No |
| Change email fails | Worker retries 3 times, then logs and drops it. The reset stands and the user stays logged out | Consumed | Retried by worker |
| Old session used after reset | Rejected, since its `sessions` row is gone | n/a | n/a |
| Request already past the session check when the reset commits | May finish. The window is milliseconds and is accepted | n/a | n/a |

Decisions behind the table:

- A dropped reset job always supersedes its token, so a link whose email never arrived does not stay usable for 30 minutes.
- The hourly limit counts emails issued, not emails delivered. A link that never arrives still uses a slot.
- There is no per-IP limit on the forgot endpoint. The per-account limit caps email volume. An endpoint-level limit can be added separately.

## Open questions

- Is the email queue a Postgres table, and how does the worker find unsent jobs? The brief does not say. If the queue is not in Postgres, the same-transaction guarantee fails and an outbox table is needed.
- Which breached-password list is used: a local copy, or a service that receives only part of a hash? The brief does not say.
- Where does the worker's counted alert go, and who owns it? The brief does not say.
- Do existing `users.email` values store lowercase addresses? If not, the lookup needs a case-insensitive match.
- What is the session cookie's name and format? The design assumes it identifies the user's `sessions` row.