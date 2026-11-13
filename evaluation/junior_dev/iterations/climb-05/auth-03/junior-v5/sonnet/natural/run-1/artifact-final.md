# Password reset by emailed link

Today a user who cannot log in has no way to recover. This adds "Forgot password?". The user enters an email address. The API server creates a one-time link, valid for 30 minutes, and queues an email with it. The existing email worker sends the email. The user clicks the link, sees a "choose a new password" page, and submits a new password. The server then saves it, ends all of the user's logins and sends them to the login page. Only a hash of the link's token is stored, so a database leak does not give anyone a working link.

The existing system: the web client talks to the API server. Postgres holds `users` (with the password hash) and `sessions` (one row per logged-in device). The API checks `sessions` on every request. To send mail, the API adds a job to the email queue. The email worker sends it through a third-party mail provider. If a send fails, the worker retries 3 times with backoff, then logs it and drops the job. Nobody is told.

## Terms

- **Raw token**: 32 random bytes from a secure random generator, base64url-encoded so it is safe in a URL. It exists only in the emailed link and in the queued job that builds the link.
- **Token hash**: the SHA-256 of the raw token. This is all the database keeps.
- **Consumed**: a token row is consumed when `consumed_at` is set. That happens when the link is used or when a newer link replaces it. A consumed token is dead.
- **Generic reply [G]**: HTTP 200 with the text "If an account exists for that address, we've sent a link." It is the same for unknown addresses, over-limit requests and success, so it reveals nothing about which accounts exist.
- **Expired page [E]**: the page "this link has expired, request a new one". It is shown for any bad token (invalid, expired, used or replaced), with no detail on which.
- **Breach list**: the list of known-breached passwords. The design only needs a yes/no lookup against it.

## Design

```
A. REQUEST  (POST /forgot-password {email})

 Client                 API server                         Postgres            Email queue -> Worker -> Mail provider
   |  email                 |                                   |                        |
   |----------------------->| normalize email (trim, lowercase) |                        |
   |                        |--- find user by email ----------->|                        |
   |                        |<-- user / none -------------------|                        |
   |                        |                                                            |
   |                        | none?  ------------------------------------> [G] generic reply, nothing sent
   |                        |                                   |                        |
   |                        | raw = 32 random bytes (CSPRNG), base64url-encoded           |
   |                        |== BEGIN ==========================|                        |
   |                        |--- lock user row (FOR UPDATE) --->|  (serializes parallel requests)
   |                        |--- count tokens for user          |
   |                        |    WHERE created_at > now-1h ---->|                        |
   |                        | count >= 3? -> ROLLBACK --------------------> [G] generic reply, no token, no email
   |                        |--- mark earlier unused tokens     |
   |                        |    consumed_at = now ------------>|  (old links die here)
   |                        |--- insert new token row:          |
   |                        |    sha256(raw), expires=now+30m ->|
   |                        |== COMMIT =========================|                        |
   |                        |--- enqueue "reset" job {email, raw} ----------------------->|
   |                        |                                                            |--> worker builds link
   |<-----------------------| [G] generic reply                                          |    APP_URL/reset?token=raw
   |                        |                                                            |    and sends; retry x3 w/ backoff
   |                        |                                                            |    then log + drop (existing)

B. LINK CLICK  (GET /reset?token=RAW)            C. SUBMIT  (POST /reset {token, new password})

 Client            API server           Postgres        Client            API server               Postgres
   |--- GET --------->| h = sha256(RAW)     |              |--- POST -------->| h = sha256(RAW)        |
   |                  |-- find h: unused,   |              |                  |-- same validity check->|
   |                  |   not expired? ---->|              |                  |   invalid -> [E]       |
   |                  |<-- yes / no --------|              |                  | len >= 12 ?            |
   |                  | no -> [E]           |              |                  | not on breach list ?   |
   |<-- "choose a new |                     |              |<-- 400 + reason -|  no -> link stays      |
   |    password" form| (GET changes        |              |    (retry OK)    |  usable, nothing       |
   |    (token in a   |  nothing)           |              |                  |  written               |
   |    hidden field) |                                     |                  | hash new password      |
                                                            |                  |== BEGIN ===============|
                                                            |                  |-- UPDATE token SET     |
                                                            |                  |   consumed_at=now      |
                                                            |                  |   WHERE hash=h AND     |
                                                            |                  |   consumed_at IS NULL  |
                                                            |                  |   AND expires_at>now   |
                                                            |                  |   RETURNING user_id -->|
                                                            |                  | 0 rows -> ROLLBACK, [E]|
                                                            |                  |-- UPDATE users         |
                                                            |                  |   password_hash ------>|
                                                            |                  |-- DELETE sessions      |
                                                            |                  |   WHERE user_id ------>| (all devices)
                                                            |                  |== COMMIT =============>|
                                                            |                  |-- enqueue "password changed" email {email} -> queue
                                                            |<-- 302 /login ---|  (no auto-login)

 [E] = expired page (invalid, expired, used or replaced token)
 [G] = generic reply (200)
```

## Stored data

One new table, `password_reset_tokens`:

| column | purpose |
|---|---|
| `id` | primary key |
| `user_id` | FK to `users` |
| `token_hash` | token hash, unique and indexed |
| `created_at` | used for the rolling-hour count |
| `expires_at` | `created_at + 30 min` |
| `consumed_at` | null while the link is usable |

Nothing is added to `users` or `sessions`. A row exists only when an email was actually issued, so "rows for this user in the last hour" is the rate-limit count and no separate counter is needed. Rows are kept after expiry, because deleting them would make the count wrong. A periodic cleanup may delete rows older than a day.

## Notes on the flows

- **Request (A).** The raw token is made once per request that finds a user, before the transaction. The transaction locks the user row first, so two simultaneous requests cannot both pass the count check or both leave a live link. Inside it: count the last hour's rows, and if 3 or more, roll back and send [G]. Otherwise mark older unused tokens consumed, insert the new row and commit. Then enqueue the job and send [G]. Unknown and over-limit requests skip the enqueue. Enqueuing is asynchronous, so response times stay close.
- **The job.** The `reset` job carries the email address and the raw token. The worker builds `APP_URL/reset?token=<raw>` from it. `APP_URL` is the app's public base URL from configuration. The "password changed" job carries only the email address, no token.
- **Link click (B).** The server hashes the token and checks the row is unused and not expired. If so it shows the form, with the token in a hidden field. If not, it shows [E]. A GET never consumes the token, because mail scanners and link previewers open links. Only the POST burns it.
- **Submit (C).** The browser sends the token back in the body of `POST /reset`. No cookie is used. The server checks the token again, then the password rules (at least 12 characters, not on the breach list). A rejected password gets a 400 with the reason, the form is shown again and the link stays usable until it expires. If the breach-list lookup is unavailable, treat the password as rejected ("try again shortly"), never accept it unchecked.
- **Single use under races.** The `UPDATE ... WHERE consumed_at IS NULL AND expires_at > now RETURNING` is the real check. The earlier read only gives a friendly error. If two submits race, or a new link request lands mid-submit, exactly one wins and the rest see [E].
- **Logout.** The password change, the token burn and the session delete happen in one transaction. Because the API checks `sessions` on every request, every device is logged out at once, including the one that did the reset. The user is redirected to the login page and is not logged in automatically. The "password changed" email is sent after commit.
- **Token handling.** Do not log job payloads or URLs with the query string. Send `Referrer-Policy: no-referrer` on the reset page. Remove the job payload once it is sent or dropped.

## What happens when things fail

| Failure | Result |
|---|---|
| DB error in the request flow | Return 503. The client shows a "try again" message. It is the same for every address, so it leaks nothing. No email is sent. |
| Enqueue fails after commit | Log it and send [G] anyway. The new row stays, so this attempt counts toward the limit of 3. The earlier link was already killed, so the user has no working link until they request again. |
| Mail provider fails | The worker retries 3 times, then logs and drops the job. The user sees nothing and has no link. They must request again, and each attempt uses quota. |
| Token bad on GET or POST | Show [E]. |
| Password too short or breached | 400 with the reason and the form again. The link stays valid. |
| Transaction fails at submit | Roll back. Password, token and sessions are unchanged, and the user can retry. |
| "Password changed" email fails to enqueue or send | The reset stays successful and the redirect still happens. Log it. This email is only a notification. |

## Open issue

The existing worker drops failed sends silently, so a user can use up their 3 emails per hour without getting a link. The worker is not changed, since the brief treats it as fixed. Recommendation: alert on dropped `reset` jobs, so a mail-provider outage is noticed by us and not only by users.

## Open questions

- Where the breach list lives (local file, database table or external service) and how it is queried is not decided.
- How the session mechanism identifies a request (cookie name, session id format) is not described. The design relies only on the brief's statement that the API checks a `sessions` row on every request.
- The value of `APP_URL` per environment is not specified.
