# Password reset by emailed link: design

```
DATA (Postgres, one new table; users and sessions already exist)
  password_reset_tokens
    id          pk
    user_id     fk -> users
    token_hash  sha256(token), unique, indexed
    created_at
    expires_at  = created_at + 30 min
    used_at     null until the link is burned (used OR superseded)
  index (user_id, created_at)   -> rate-limit count

==========================================================================
A. REQUEST FLOW   "Forgot password?"
==========================================================================
 Browser                 API server                 Postgres        Email queue -> worker -> provider
    |  POST /forgot {email}  |                          |
    |----------------------->|  find user by email      |
    |                        |------------------------->|
    |                        |                          |
    |            .-----------+-- no such user? ----------> (do nothing, no job)
    |            |           |
    |            |   BEGIN; SELECT user FOR UPDATE      (serialises concurrent requests)
    |            |   count rows in password_reset_tokens
    |            |     where user_id=U and created_at > now()-1h
    |            |           |
    |            |      count >= 3 ? --yes--> ROLLBACK, no link, no job
    |            |           |
    |            |          no
    |            |           v
    |            |   UPDATE tokens SET used_at=now()
    |            |     WHERE user_id=U AND used_at IS NULL     (kills older links)
    |            |   token = 32 random bytes
    |            |   INSERT (user_id, sha256(token), now, now+30m)
    |            |   enqueue job {to, raw token link}  --------------> queue
    |            |   COMMIT  (if enqueue fails: ROLLBACK, old link survives, log)
    |            |           |                                           |
    |            '-----------+---- every branch converges ---+           v
    |<-----------------------|  200 "If an account exists for that     worker sends via provider
    |   same body, same status    address, we've sent a link."           fail -> retry x3 w/ backoff
    |                                                                    still failing -> log, DROP
    |                                                                    (nobody notified)

==========================================================================
B. LINK-CLICK FLOW   (two checks: page load, then submit)
==========================================================================
 Browser                 API server                         Postgres
    | GET /reset?token=T    |
    |---------------------->| h = sha256(T)
    |                       | SELECT row WHERE token_hash=h
    |                       |   AND used_at IS NULL AND expires_at > now()   (read only, burns nothing)
    |                       |-------------------------------->|
    |                       |
    |            valid? --no (unknown / expired / used / superseded)--> [EXPIRED PAGE]
    |                       |                                  "This link has expired, request a new one"
    |                      yes
    |<----------------------| [CHOOSE NEW PASSWORD PAGE]  (Referrer-Policy: no-referrer,
    |                       |  token kept in a hidden field, stripped from the URL bar)
    |                       |
    | POST /reset {T, pw}   |
    |---------------------->| 1. re-check token as above --no--> [EXPIRED PAGE]
    |                       | 2. pw >= 12 chars?  not on breached list?
    |                       |      no --> re-show form + reason, link stays usable
    |                       |             (user may retry until expiry)
    |                       | 3. BEGIN
    |                       |    UPDATE tokens SET used_at=now()
    |                       |      WHERE token_hash=h AND used_at IS NULL
    |                       |        AND expires_at > now()   RETURNING user_id
    |                       |      0 rows (lost a race / just expired)
    |                       |        --> ROLLBACK -> [EXPIRED PAGE]
    |                       |    UPDATE users SET password_hash=hash(pw)
    |                       |    DELETE FROM sessions WHERE user_id=U   (all devices, incl. this one)
    |                       |    COMMIT
    |                       | 4. enqueue "your password was changed" email  -> queue (as in A)
    |<----------------------| 302 -> /login   (no session is created)

==========================================================================
C. FAILURE PATHS
==========================================================================
 Unknown email ............ generic message, no row, no job
 Over 3 in rolling hour ... generic message, no row, no job, older link untouched
 Enqueue fails ............ ROLLBACK, generic message, error logged; old link still valid
 Mail send fails .......... worker retries 3x, then drops silently; user sees only the
                            generic message and can request again (counts toward the 3/hr)
 Link invalid/expired/used  expired page, at load and again at submit
 Two new requests quickly . only the newest link works; older one -> expired page
 Double-submit / two tabs . conditional UPDATE lets exactly one win; the other -> expired page
 Weak or breached password  form re-shown with reason; link not burned
 Breach-list lookup down .. fail closed: "try again" on the form, link not burned
 DB error on submit ....... transaction rolls back; password, link and sessions unchanged
 "Changed" email lost ..... password is already changed; failure only logged
```

## Notes

- **Storage.** One new table, `password_reset_tokens`. The raw token exists only in the emailed link, the queue job payload and the user's browser. Only its SHA-256 hash is stored. Superseded links get `used_at` set, and rows are never deleted inside the hour, so the same table serves as the rate-limit counter. A nightly job can purge rows older than a day.
- **Concurrency.** `SELECT ... FOR UPDATE` on the user row serialises concurrent requests, so the 3-per-hour limit and "newest link only" hold even under parallel requests. The burn is a single conditional `UPDATE ... RETURNING`, so a link works once even with a double submit.
- **No enumeration.** Every branch returns the same status and body. Keep the response time similar for unknown and known addresses, for example by doing the DB work but not waiting for the enqueue. Don't log or rate-limit differently in a way that is visible to the client.
- **GET is read-only.** Mail scanners and link previewers often open links. Because loading the page doesn't burn the token, they can't use it up. Only the POST consumes it.
- **Token in the queue.** The job payload has to carry the raw token, since we keep only the hash. Don't log job bodies, and delete the payload once the job is sent or dropped.
- **Session kill.** The API checks `sessions` on every request, so deleting the rows logs out every device immediately. This includes the device that did the reset. The user must log in again.
- **Known gap: silent email failure.** The worker drops failed jobs without telling anyone. The user gets the generic message and no link, and nothing in this design alerts them or us. Mitigation within the requirements: users can re-request, and each failed attempt still counts toward the 3/hr limit. I recommend adding an alert on dropped reset jobs. It needs a small worker change, which is outside this scope.
- **Known gap: "password changed" email.** It's sent after commit. If it's dropped, the user is never told, which matters most if the reset wasn't theirs. The same alert would cover it.
