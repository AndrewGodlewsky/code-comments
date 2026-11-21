# Design: Password reset by emailed link

## 1. Components

```
 +-------------+                 +------------------+                 +-------------------+
 | Web client  | --- HTTPS ----> | API server       | ----- SQL ----> | Postgres          |
 |             | <-- pages ----- | /password-reset  |                 | users             |
 +-------------+                 +--------+---------+                 | sessions          |
                                          |                           | password_reset_   |
                                          | add job                   |   tokens          |
                                          v                           +-------------------+
                                 +------------------+
                                 | Email queue      |   (existing)
                                 +--------+---------+
                                          | claim job
                                          v
                                 +------------------+                 +-------------------+
                                 | Email worker     | ---- send ----> | Mail provider     |
                                 | 3 retries, then |                 +-------------------+
                                 | log and drop    |
                                 +------------------+
```

## 2. Request flow: POST /password-reset/request {email}

```
 Client            API                         Postgres                 Queue
   |  {email}        |                            |                       |
   |---------------->|  normalise email           |                       |
   |                 |  BEGIN                     |                       |
   |                 |  SELECT user FOR UPDATE -->|  (serialises requests |
   |                 |<-- user | none ------------|   for this account)   |
   |                 |                            |                       |
   |                 |  no user ----------------------> COMMIT, go to reply|
   |                 |  SELECT count(*) of tokens |                       |
   |                 |    created in last 1 h --->|                       |
   |                 |<-- n ----------------------|                       |
   |                 |  n >= 3 ----------------------> COMMIT, go to reply |
   |                 |  n < 3:                    |                       |
   |                 |    token = 32 bytes CSPRNG |                       |
   |                 |    UPDATE old unused tokens|                       |
   |                 |      SET revoked_at = now()|                       |
   |                 |    INSERT token row        |                       |
   |                 |      (sha256(token),       |                       |
   |                 |       expires_at=now+30m)->|                       |
   |                 |    INSERT job {token_id,   |                       |
   |                 |      token encrypted} ----------------------------->|
   |                 |  COMMIT ------------------>|                       |
   |<-- 200 "If an account exists for that address, we've sent a link." --|
```

Notes:
- The same 200 response goes out on every branch: unknown address, over limit, and success. Only the success branch writes a token and a job.
- The unknown-address branch should spend similar time to the success branch (for example, run a dummy hash) so response timing does not reveal accounts.
- The 3-per-hour limit counts issued tokens, not unused ones, so superseded links still count. The `FOR UPDATE` lock on the user row stops two concurrent requests from both passing the count.

## 3. Link-click flow

### 3a. Page load: GET /reset?t=TOKEN

```
 Browser                   API                              Postgres
   |  GET /reset?t=TOKEN     |                                   |
   |------------------------>|  h = sha256(TOKEN)                |
   |                         |  SELECT row WHERE token_hash = h  |
   |                         |    AND used_at IS NULL            |
   |                         |    AND revoked_at IS NULL         |
   |                         |    AND expires_at > now()  ------>|
   |                         |<-- row | none --------------------|
   |<-- 200 form with hidden token field (row found)             |
   |<-- 200 "this link has expired, request a new one" (none)    |
```

Loading does not consume the token.

### 3b. Submit: POST /reset {token, new_password}

```
 Browser                   API                                Postgres
   |  {token, password}      |                                     |
   |------------------------>|  1. check password: >= 12 chars,    |
   |                         |     not on breached list            |
   |                         |     reject -> 422 form again,       |
   |                         |     token NOT consumed              |
   |                         |  2. hash password (argon2id)        |
   |                         |  BEGIN                              |
   |                         |  SELECT token FOR UPDATE ---------->|
   |                         |  row missing, used, revoked, or     |
   |                         |  expired -> ROLLBACK, expired page  |
   |                         |  UPDATE users SET password_hash --->|
   |                         |  UPDATE token SET used_at = now() ->|
   |                         |  UPDATE other tokens for user       |
   |                         |    SET revoked_at = now() -------->|
   |                         |  DELETE FROM sessions WHERE         |
   |                         |    user_id = ?  (every device) ---->|
   |                         |  INSERT job "password changed"      |
   |                         |    (same transaction) ------------->|
   |                         |  COMMIT                             |
   |<-- 303 Location: /login (no session cookie is set)            |
```

Notes:
- Password checks and hashing happen before `BEGIN`, so the row lock is held only for the short write.
- The token check runs twice: once on page load for the UX, and again under lock on submit. That lock also stops a double-submit from succeeding twice.
- The "password changed" job is inserted in the same transaction, so it exists only if the reset committed. If the queue is not in Postgres, enqueue after commit instead. That leaves a small window where the notice can be lost (see open question 4).

## 4. Failure paths

| Case | Behaviour | Stored state |
|---|---|---|
| Unknown email | Generic 200, nothing sent | Nothing written |
| Over 3 per hour | Generic 200, nothing sent | Nothing written |
| Send fails, retried, then dropped | User gets no email and no notice. The token expires unused in 30 min. The user can ask again, but each request uses one of the 3 slots. | Token row stays unused until expiry |
| Provider outage | Same as above, for every user | Same |
| Newer link issued | Earlier link revoked. The worker also re-checks the token before sending and skips a superseded job. | Old row revoked |
| Link expired (30 min after issue) | Expired page on load and on submit | expires_at is fixed at issue, not extended |
| Link already used | Expired page | used_at set |
| Weak or breached password | 422, form again. Link still works until expiry. | Nothing changed |
| Double-submit or race | Lock serialises them. The second gets the expired page. | Only one reset applies |
| DB error mid-transaction | Rollback. Password, token, and sessions all unchanged. | Unchanged |
| Session cache in API (if any) | Deleted sessions must stop working at once | Invalidate the cache on delete, or do not cache |

## 5. Data

- `password_reset_tokens`: `id` (uuid, pk), `user_id` (fk to users), `token_hash` (bytea 32, unique), `created_at`, `expires_at` (created_at + 30 min), `used_at` (nullable), `revoked_at` (nullable). Index on `(user_id, created_at)` for the rate limit. Purge rows older than 24 h.
- `users`: only `password_hash` changes.
- `sessions`: unchanged schema. A reset deletes all rows for the user.
- Email job payload: `{kind, token_id, user_id, token_ciphertext}`. Encrypt the token with an application key. Delete the job when it is sent or dropped. Worker logs must never include the link or token.
- SHA-256 is enough for the hash because the token already carries 256 bits of randomness.

## 6. Link handling

- Use a 43-character base64url encoding of the 32 bytes.
- Set `Referrer-Policy: no-referrer` on reset pages so the token does not leak to third parties.
- The form posts the token as a hidden field, not in the query string, and no query string is logged.

## 7. Open questions

1. **Raw token in the queue.** The design keeps the raw token inside an encrypted job payload until the job finishes. The alternative is to have the worker mint the token and store only its hash. The alternative avoids a raw token in the queue at all but is more complex. Decide before build.
2. **Silent drops.** A dropped email gives no signal. Proposal: alert on dropped reset jobs and expose a metric. Decide whether failed sends should free up a quota slot.
3. **Breached-password source.** Options are a hosted k-anonymity range API or a local list. Pick one and state its refresh rule.
4. **Queue location.** If the queue is outside Postgres, the "password changed" notice needs enqueue-after-commit, and a crash between commit and enqueue loses it. Confirm where the queue lives.
5. **Rate limit by IP.** The brief does not ask for it, but a per-IP limit on the request endpoint would reduce abuse. Left out to keep scope.