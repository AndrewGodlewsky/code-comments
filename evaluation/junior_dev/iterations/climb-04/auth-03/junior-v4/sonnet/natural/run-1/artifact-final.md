# Password reset by emailed link

A user who cannot log in enters their email address. If an account exists, the API creates a one-time link that lasts 30 minutes and queues an email containing it. The link opens a "choose a new password" page. On submit, the API saves the new password, burns the link, logs the account out everywhere and queues a "password changed" email.

Today: the web client talks to the API server. Postgres holds `users` (with the password hash) and `sessions` (one row per logged-in device, checked on every request). Mail goes through an email queue: the API adds a job, and a worker sends it through the mail provider. A failed send is retried 3 times with backoff, then the job is logged and dropped. Nobody is notified.

## Terms

- **Reset link**: a URL holding a random token (32 random bytes). The raw token exists only in the link, the page's hidden form field and the queued job. It is never logged.
- **Token hash**: the SHA-256 of the token. This is all we store.
- **Live link**: unused, not killed and not yet expired.
- **Killed link**: replaced by a newer link for the same account.
- **Generic reply**: HTTP 200 with the message "If an account exists for that address, we've sent a link." Every outcome of the request flow returns this exact reply.

## Data

One new table. `users` and `sessions` already exist.

```
password_resets(id, user_id, token_hash UNIQUE,
                issued_at, expires_at = issued_at + 30m,
                used_at NULL, killed_at NULL)
```

A link is live when `used_at IS NULL AND killed_at IS NULL AND now() < expires_at`.

## Flow A: request a link   (POST /forgot-password {email})

```
 Client          API server                       Postgres      Queue -> worker -> provider
   | email          |                                |
   |--------------->| 1. trim + lowercase email      |
   |                | 2. look up user -------------->| users
   |                |    no user: go to step 7       |
   |                | 3. BEGIN; lock user row        |
   |                |    (FOR UPDATE) ------------->|
   |                | 4. count password_resets for   |
   |                |    this user, any state,       |
   |                |    issued in the last hour     |
   |                |    count >= 3: ROLLBACK,       |
   |                |    go to step 7 (no row, no job)
   |                | 5. kill older live links:      |
   |                |    SET killed_at = now()       |
   |                |    insert new row (token hash) |
   |                |    COMMIT -------------------->|
   |                | 6. enqueue reset job --------------------> queue
   |                |    {address, link}; not awaited            worker sends
   |                |                                            (3 retries, then drop)
   |  200 generic   | 7. reply (same status, body    |
   |<---------------|    and shape on every path)    |
```

## Flow B: use the link   (GET /reset?token=T, then POST /reset)

```
 Browser          API server                            Postgres
   | GET T          |
   |--------------->| 1. hash T, find row by token_hash ->|
   |                | 2. link live?
   | form  <--------|    yes: show form, T in hidden field
   | expired page <-|    no (unknown/expired/used/killed): "this link has
   |                |    expired, request a new one"   (this check only chooses the page)
   |
   | POST T + new password
   |--------------->| 3. hash T, find row; link not live: "expired" page, stop
   |                | 4. password < 12 chars or on breached list:
   |                |    re-show form with error; link untouched
   |                |    (list unreachable: generic "try again later", link untouched)
   |                | 5. BEGIN
   |                |    UPDATE password_resets SET used_at = now()
   |                |      WHERE id = row.id AND link is live
   |                |      0 rows changed: ROLLBACK, "expired" page, stop
   |                |    UPDATE users SET password_hash = hash(new)
   |                |    DELETE FROM sessions WHERE user_id = ?  (all devices)
   |                |    COMMIT -------------------------->|
   |                | 6. enqueue "password changed" job
   |                |    {address from users, fixed text, no link}
   | 302 /login <---| 7. redirect; no session is created
```

## What happens when things fail

| Case | Result |
|---|---|
| Unknown email | Generic reply. Nothing stored or sent. |
| 3 links already in the last hour | Generic reply. No row, no job. The earlier link is unchanged. |
| DB error on request | Transaction rolls back, no job. Generic reply. Log and alert. |
| Enqueue fails (queue down) | The row is already committed. Generic reply. Log and alert. No retry. |
| Send fails | Worker retries 3 times, then drops the job. The user sees nothing and may request again (counts toward the 3 per hour). |
| Token bad, expired, used or killed (page load or submit) | "Link expired" page. |
| Two submits of one link at once | The conditional `UPDATE` of `used_at` lets one win. The other gets "link expired". |
| Weak or breached password | Form re-shown with an error. Link stays live until it expires. |
| DB error on submit | Whole transaction rolls back (hash, link and sessions unchanged). Form re-shown with a generic error. Log. Link stays live. |
| "Password changed" email fails (enqueue or send) | The reset is already committed. Same handling as above. The user is still redirected to login. |

## Notes

- **Rate limit.** Each issued link is one row, so counting rows in the last hour needs no separate counter. The user-row lock stops two parallel requests from both passing the count.
- **One live link.** A new link kills the older live ones in the same transaction. A user who clicks an older link sees the "expired" page, which tells them to request a new one.
- **Single use.** The page-load check only chooses what to show. The submit check is the real one, and the conditional `UPDATE` enforces single use under concurrency. Check the password on the server even if the client also checks. Rejected passwords never consume the link.
- **Atomic reset.** The new hash, the burned link and the deleted sessions commit together. The API checks `sessions` on every request, so a deleted session is logged out on its next request.
- **Timing.** The enqueue is not awaited. The found-user path still does a transaction, so a small timing difference remains. We accept that: the brief only fixes the response content.
- **Known gap.** The worker drops failed jobs silently. A user whose reset email never arrives gets no signal and may hit the 3 per hour limit. If the "password changed" email fails, the user may not learn of an unauthorised change. This design does not change the worker. The minimum fix is an alert on dropped reset and password-changed jobs.
- **Housekeeping (optional).** Delete `password_resets` rows older than a day.

## Open questions

- Where the breached-password list lives (table, file or service) is not decided.
- Which hash function login uses is not stated here. Reset must use the same one.
- Whether `users.email` is stored trimmed and lowercased is not known. The lookup must match however it is stored.
- Whether the queue keeps job payloads (with raw tokens) after sending or dropping is not known. If it does, they need clearing.
- Whether the client sends its session as a cookie or a header is the existing system's choice and is not described here.
