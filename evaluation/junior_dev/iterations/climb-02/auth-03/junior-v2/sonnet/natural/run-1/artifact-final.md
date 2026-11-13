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
  At most one live link per user exists at any time (a new link kills the old one).

==========================================================================
A. REQUEST FLOW   "Forgot password?"
==========================================================================
 Browser                 API server                 Postgres        Email queue -> worker -> provider
    |  POST /forgot {email}  |                          |            (queue and worker already exist,
    |----------------------->|  find user by email      |             worker is a separate process, unchanged)
    |                        |------------------------->|
    |                        |                          |   (email trimmed + lowercased first)
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
    |            |   link = https://<app>/reset?token=<raw token>   (API builds it)
    |            |   enqueue job {to, link}  -------------------------> queue (separate from Postgres)
    |            |   COMMIT  (if enqueue fails: ROLLBACK, old link survives, log)
    |            |           |                                           |
    |            '-----------+---- every branch converges ---+           v
    |<-----------------------|  200 "If an account exists for that     worker sends via provider
    |   same body, same status    address, we've sent a link."           fail -> retry x3 w/ backoff
    |   (client shows the body)                                          still failing -> log, DROP
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
    |<----------------------| [CHOOSE NEW PASSWORD PAGE]  Referrer-Policy: no-referrer.
    |                       |  Server puts T in a hidden form field; page script then
    |                       |  calls history.replaceState to remove it from the URL bar.
    |                       |
    | POST /reset {T, pw}   |   (no login needed, the token is the credential.
    |---------------------->|    Every retry starts at step 1.)
    |                       | 1. re-check token as above --no--> [EXPIRED PAGE]
    |                       | 2. pw >= 12 chars?  not on breached list?
    |                       |      no --> re-show form + reason, link stays usable
    |                       |             (user may retry until expiry)
    |                       | 3. BEGIN
    |                       |    UPDATE tokens SET used_at=now()
    |                       |      WHERE token_hash=h AND used_at IS NULL
    |                       |        AND expires_at > now()   RETURNING user_id  (= U)
    |                       |      0 rows (lost a race / just expired)
    |                       |        --> ROLLBACK -> [EXPIRED PAGE]
    |                       |    UPDATE users SET password_hash=hash(pw) WHERE id=U
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
 COMMIT fails after enqueue  generic message; the email may still go out but its link shows
                            the expired page (accepted, rare); user can request again
 Mail send fails .......... worker retries 3x, then drops silently; user sees only the
                            generic message and can request again (counts toward the 3/hr)
 Link invalid/expired/used  expired page, at load and again at submit
 Two new requests quickly . only the newest link works; older one -> expired page
 Double-submit / two tabs . conditional UPDATE lets exactly one win; the other -> expired page
 Weak or breached password  form re-shown with reason; link not burned
 Breach-list lookup down .. fail closed: form re-shown with "try again later", link not burned
 DB error on submit ....... transaction rolls back; password, link and sessions unchanged
 "Changed" email fails .... password is already changed and the 302 to /login still happens;
                            failure only logged
```

## Notes

- **Storage.** The raw token exists only in the emailed link, the queue job payload and the user's browser; the table holds only its SHA-256 hash. Superseded links get `used_at` set and rows are not deleted inside the hour, so the same table is the rate-limit counter. A nightly job can purge rows older than a day.
- **Concurrency.** `SELECT ... FOR UPDATE` on the user row makes the 3-per-hour limit and "newest link only" hold under parallel requests. The burn is one conditional `UPDATE ... RETURNING`, so a link works once even with a double submit.
- **No enumeration.** Every branch returns the same status and body. Similar response time for known and unknown addresses is a recommendation, not a requirement (for example, don't wait for the enqueue). Don't log or rate-limit differently in a way the client can see.
- **GET is read-only.** Mail scanners and link previewers open links; because loading the page burns nothing, they can't use the token up. Only the POST consumes it.
- **Token in the queue.** The job carries the finished link (so the raw token) because we keep only the hash. Don't log job bodies, and make sure the queue keeps no payload after a job is sent or dropped.
- **Session kill.** The API checks `sessions` on every request, so deleting the rows logs out every device immediately, including the one that reset. The user must log in again.
- **Known gap: silent email failure.** The worker drops failed jobs without telling anyone. This affects both the reset link and the "password changed" email, which matters most if the reset wasn't the user's. Within the requirements, the mitigation is that users can re-request (each failed attempt counts toward 3/hr). I recommend an alert on dropped reset jobs; it needs a small worker change, outside this scope.

## Open questions

- Where does the breached-password list live (local file, table or service)? The design only needs a yes/no lookup.
- Is `users.email` unique, and is it already stored lowercased? The design assumes one user per normalised address.
- How does our queue remove payloads after send or drop? Needs confirming with the queue owner.