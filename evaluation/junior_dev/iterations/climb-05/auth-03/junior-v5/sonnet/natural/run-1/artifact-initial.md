# Password reset by emailed link

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
   |                        |--- enqueue "reset" job (raw token in link) --------------->|
   |                        |                                                            |--> worker sends
   |<-----------------------| [G] generic reply: "If an account exists for that          |    retry x3 w/ backoff
   |                        |     address, we've sent a link."                           |    then log + drop (existing)

B. LINK CLICK  (GET /reset?token=RAW)            C. SUBMIT  (POST /reset {token, new password})

 Client            API server           Postgres        Client            API server               Postgres
   |--- GET --------->| h = sha256(RAW)     |              |--- POST -------->| h = sha256(RAW)        |
   |                  |-- find h: unused,   |              |                  |-- same validity check->|
   |                  |   not expired? ---->|              |                  |   invalid -> [E]       |
   |                  |<-- yes / no --------|              |                  | len >= 12 ?            |
   |                  | no -> [E]           |              |                  | not on breach list ?   |
   |<-- "choose a new |                     |              |<-- 400 + reason -|  no -> link stays      |
   |    password" form| (GET changes        |              |    (retry OK)    |  usable, nothing       |
   |    (token kept   |  nothing)           |              |                  |  written               |
   |    in the form)  |                                     |                  | hash new password      |
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
                                                            |                  |-- enqueue "password changed" email -> queue
                                                            |<-- 302 /login ---|  (no auto-login)

 [E] = "this link has expired, request a new one" page (invalid, expired, used or replaced token)
```

## Stored data

One new table, `password_reset_tokens`:

| column | purpose |
|---|---|
| `id` | primary key |
| `user_id` | FK to `users` |
| `token_hash` | SHA-256 of the raw token, unique and indexed |
| `created_at` | used for the rolling-hour count |
| `expires_at` | `created_at + 30 min` |
| `consumed_at` | null while the link is usable. It is set on use or when a newer link replaces it. |

- Nothing is added to `users` or `sessions`.
- A row exists only when an email was actually issued. So "rows for this user in the last hour" is the rate-limit count, and no separate counter is needed.
- Rows are kept past expiry. Without them the hourly count would be wrong. A periodic cleanup can delete rows older than a day.

## Notes on the flows

- **Rate limit and one live link.** The count, the invalidation of the old link and the insert run in one transaction. The transaction first locks the user row, so two simultaneous requests cannot both pass the check or both leave a live link.
- **Generic reply.** Unknown address, over-limit and success all return the same body and status. Both the unknown and the over-limit paths skip the enqueue. Enqueuing is asynchronous, so response times stay close.
- **GET never consumes the token.** Mail scanners and link previewers open links. Only the POST burns the token.
- **Single use under races.** The `UPDATE ... WHERE consumed_at IS NULL AND expires_at > now RETURNING` statement is the real check. The earlier validity read only produces a friendly error. If two submits race, or a new link request lands mid-submit, exactly one wins and the rest see [E].
- **Rejected password.** The token is not touched, so the user can retry until it expires. If the breach-list lookup is unavailable, treat the password as rejected ("try again shortly") rather than accept it unchecked. The link stays usable.
- **Session logout.** The API checks `sessions` on every request. Deleting the rows in the same transaction as the password change logs out every device immediately, including the one that did the reset.
- **Token handling.** The raw token exists only in the email link and in the queued job payload that builds it. Do not log job payloads or URLs with the query string. Send `Referrer-Policy: no-referrer` on the reset page. The job payload should be removed once it is sent or dropped.

## Failure paths

| Failure | Result |
|---|---|
| DB error in the request flow | Return a generic "try again" error (503). It is the same for every address, so it leaks nothing. No email is sent. |
| Enqueue fails after commit | Log it and return the generic message anyway. The token row stays, so this attempt counts toward the limit of 3. The user can request again. |
| Mail provider fails | The worker retries 3 times, then logs and drops the job. The user sees nothing and has no link. They would request again, and each attempt uses quota. |
| Token invalid, expired, used or replaced (on GET or POST) | Show [E]. No detail is given about which case it was. |
| Password too short or breached | Return 400 with the reason and re-show the form. The link stays valid. |
| Transaction fails at submit | Roll back. The password, token and sessions are all unchanged, and the user can retry. |
| "Password changed" email fails to enqueue or send | The reset stays successful and the redirect still happens. Log it. This email is only a notification. |

## Open issue

The existing worker drops failed sends silently, so a user can burn their 3 emails per hour without receiving a link. I did not change the worker, since the brief treats that behavior as fixed. I recommend alerting on dropped `reset` jobs, so a mail-provider outage is noticed by us, not just by users.
