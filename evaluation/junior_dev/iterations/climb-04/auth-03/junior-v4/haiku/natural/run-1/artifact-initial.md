# Password reset by emailed link: design

## Diagram

```
FLOW 1: REQUEST A LINK

 Browser                 API server                              Postgres
   |                         |                                       |
   | POST /password-reset    |                                       |
   | { email }               |                                       |
   |------------------------>|  1. normalize email                   |
   |                         |  2. BEGIN                             |
   |                         |  3. SELECT user WHERE email           |
   |                         |     FOR UPDATE ---------------------->|
   |                         |<--------------------------------------|
   |                         |  4. user exists AND                   |
   |                         |     tokens for user created in last   |
   |                         |     1 hour < 3 ?                      |
   |                         |     no:  COMMIT, go to step 9         |
   |                         |     yes: continue                     |
   |                         |  5. raw = 32 random bytes (base64url) |
   |                         |     hash = SHA-256(raw)               |
   |                         |  6. UPDATE tokens SET invalidated_at  |
   |                         |     = now() WHERE user AND unused     |
   |                         |     AND not invalidated ------------->|
   |                         |  7. INSERT token (user, hash,         |
   |                         |     expires_at = now() + 30 min) ---->|
   |                         |  8. INSERT outbox job               |
   |                         |     (token_id, encrypted raw) ------->|
   |                         |     COMMIT ------------------------->|
   |                         |  9. reply 200 (same on every branch)  |
   |<------------------------|                                       |
   | "If an account exists for that address, we've sent a link."     |


FLOW 2: DELIVER THE EMAIL (email worker)

 outbox job --> decrypt raw token --> token still live?
                                        |            |
                                       no           yes
                                        |            |
                              drop job, log    send via mail provider
                                                     |          |
                                                   ok        fail
                                                     |          |
                                                  done    retry up to 3x
                                                          with backoff
                                                             |
                                                  still failing: log, drop job
                                                  (no notice to the user)


FLOW 3: CLICK THE LINK AND SET A PASSWORD

 Browser                       API server                          Postgres
   |                              |                                   |
   | GET /reset?token=RAW ------->| hash = SHA-256(RAW)               |
   |                              | SELECT token WHERE hash --------->|
   |                              |<----------------------------------|
   |                              | live? = unused AND not invalidated|
   |                              |         AND expires_at > now()    |
   |<-- no:  "This link has expired. Request a new one." page        |
   |<-- yes: 200 form, token in hidden field                         |
   |        (Referrer-Policy: no-referrer)                           |
   |                              |                                   |
   | POST /reset/confirm          |                                   |
   | { token, new_password } --->| hash token                        |
   |                              | pre-check live (no lock)          |
   |                              |   not live: expired page          |
   |                              | check new_password:               |
   |                              |   >= 12 chars, not breached       |
   |<-- rejected: form error, link stays usable until it expires     |
   |                              | BEGIN                             |
   |                              | SELECT token WHERE hash FOR UPDATE|
   |                              |   ------------------------------->|
   |                              | re-check live (authoritative)     |
   |                              |   not live: ROLLBACK, expired page|
   |                              | UPDATE users SET password_hash,   |
   |                              |        password_changed_at = now()|
   |                              | DELETE sessions WHERE user_id     |
   |                              | UPDATE token SET used_at = now()  |
   |                              | INSERT outbox "password changed"  |
   |                              | COMMIT ---------------------------->|
   |<-- 303 redirect to /login (no automatic login)                  |
```

## Data

- `password_reset_tokens` (new): `id`, `user_id` (FK to users), `token_hash` (bytea, 32 bytes, unique), `created_at`, `expires_at`, `used_at` (nullable), `invalidated_at` (nullable). Index on `(user_id, created_at)`.
- The token table doubles as the rate-limit ledger. Rows are kept after use or invalidation so the "3 in the last hour" count stays correct. Purge rows older than about 24 hours.
- `users` (changed): add `password_changed_at`.
- `sessions`: no schema change. Reset deletes all rows for the user.
- Outbox job payload: `token_id` and the raw token encrypted with an app key. See open issue 1.

## Failure paths

| Case | Behavior |
|---|---|
| Unknown email | No row, no token, no email. Same generic reply. Keep timing close to the known-user path. |
| Over 3 per hour | Generic reply. No token is created and no email is queued. |
| Email send fails 3 times | Job is logged and dropped. The user still sees the generic message. Their link stays valid but unseen, and it expires in 30 minutes. |
| Link invalid, expired or used on page load | "This link has expired. Request a new one." page. |
| Newer link issued | Older link is invalidated at issue time and shows the expired page. |
| Link expires while the form is open | Submit re-checks the token and shows the expired page. |
| Weak or breached password | Form error. Token is not consumed. The user can retry until expiry. |
| Two submits at once | `FOR UPDATE` on the token row. The second submit sees `used_at` set and gets the expired page. |
| DB error during the reset transaction | Full rollback. Token stays unused, password unchanged, no session deleted. |
| "Password changed" email fails | Reset still stands. Log it. The email goes through the same retry and drop path. |
| Login racing the reset | A login that read the old hash may create a session after the delete. Session check rejects any session with `created_at` before `password_changed_at`. |

## Open issues and decisions

1. **The raw token must sit in the queue until the email is sent.** The worker needs it to build the link. The brief says the raw token appears only in the link. Options: encrypt the payload with an app key, delete it on send, and keep retention short (recommended). Or send the email synchronously, which gives up the queue. This needs a decision.
2. **The quota counts issued links, not delivered emails.** A send that is later dropped still uses one of the 3 slots. Confirm this is acceptable.
3. **A dropped email is silent to the user.** The brief says nobody is notified. Ops should still get an alert or metric on dropped reset and password-changed jobs. Consider a "didn't get the email?" path.
4. **The token is in the URL.** Keep query strings out of access logs and error reports. The `no-referrer` header stops it leaking to third-party assets on the form page.
5. **No per-IP limit is specified.** The 256-bit token makes guessing infeasible. Still, a per-IP limit on the request and confirm endpoints would reduce abuse.
6. **The breached-password check.** Use a k-anonymity range lookup or a local list, and run it outside the database transaction so no lock is held during the network call.