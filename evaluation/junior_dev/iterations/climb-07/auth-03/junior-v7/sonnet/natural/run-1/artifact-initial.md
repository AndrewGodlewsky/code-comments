# Password reset by emailed link: design

```
DATA (Postgres, one new table)
  password_reset_tokens
    token_hash   bytea PRIMARY KEY      -- SHA-256 of the raw token
    user_id      FK -> users
    issued_at    timestamptz
    expires_at   timestamptz            -- issued_at + 30 min
    used_at      timestamptz NULL       -- set when burned OR superseded
  index (user_id, issued_at)
  Rows are kept at least 1 hour (they are the rate-limit record).

======================================================================
1. REQUEST FLOW   POST /forgot-password {email}
======================================================================

 Browser            API server                    Postgres        Email queue -> Worker -> Mail provider
    |  email           |                             |
    |----------------->|                             |
    |                  | normalize email (trim, lowercase)
    |                  |-- find user by email ------>|
    |                  |<-- user / none -------------|
    |                  |
    |          +-------+--------------------------+
    |          | no user? ---------------------------------> (A) skip to response
    |          +------------------------------------+
    |                  | BEGIN
    |                  |-- SELECT user FOR UPDATE -->|   (serializes concurrent requests
    |                  |                             |    for the same account)
    |                  |-- count tokens WHERE        |
    |                  |   user_id AND issued_at     |
    |                  |   > now() - 1h ------------>|
    |                  |<-- n ----------------------|
    |                  |
    |          n >= 3? ----yes----> ROLLBACK -------------> (A) skip to response
    |                  | no
    |                  | raw = 32 random bytes (CSPRNG)
    |                  |-- UPDATE tokens SET used_at=now()
    |                  |   WHERE user_id AND used_at IS NULL   (kills earlier links)
    |                  |-- INSERT (sha256(raw), user_id,
    |                  |   now(), now()+30min) ----->|
    |                  | COMMIT
    |                  |-- enqueue "reset" job {user email, link containing raw} ---> queue
    |                  |
    |   (A) 200 "If an account exists for that address, we've sent a link."
    |<-----------------|     (identical body and status on all paths)
    |
    |                                                    worker: send via provider
    |                                                    fail -> retry x3 w/ backoff
    |                                                    still failing -> log, drop (existing)

======================================================================
2. LINK-CLICK FLOW   GET /reset?token=RAW   (read-only, burns nothing)
======================================================================

 Browser            API server                    Postgres
    |  GET link        |
    |----------------->|-- SELECT WHERE token_hash = sha256(RAW)
    |                  |   AND used_at IS NULL AND expires_at > now() -->|
    |                  |<-- row / none ----------------------------------|
    |                  |
    |            row?  |--yes--> "choose a new password" page (RAW kept in form)
    |                  |--no---> "this link has expired, request a new one" page
    |<-----------------|

======================================================================
3. SUBMIT FLOW   POST /reset {token, new_password}
======================================================================

 Browser            API server                          Postgres
    |  token+pw        |
    |----------------->|-- token check (same query as page load) -->|
    |                  |      invalid/expired/used --> EXPIRED PAGE  (F1)
    |                  |
    |                  | pw < 12 chars?  --------> re-show form + error (F2)
    |                  | pw on breached list? ---> re-show form + error (F2)
    |                  | breach check unavailable? -> re-show form,
    |                  |                              "try again" (F3)
    |                  |      (token untouched in F2/F3: link stays usable)
    |                  |
    |                  | BEGIN
    |                  |-- UPDATE tokens SET used_at=now()
    |                  |   WHERE token_hash AND used_at IS NULL
    |                  |   AND expires_at > now()
    |                  |   RETURNING user_id ----------->|
    |                  |      0 rows (lost a race) -> ROLLBACK -> EXPIRED PAGE (F1)
    |                  |-- UPDATE users SET password_hash = hash(pw) ->|
    |                  |-- DELETE FROM sessions WHERE user_id ------->|  (every device,
    |                  | COMMIT                                       |   incl. this one)
    |                  |-- enqueue "your password was changed" ---> queue -> worker
    |   302 -> /login  |
    |<-----------------|   (no session created, no auto-login)

======================================================================
4. FAILURE PATHS
======================================================================
 F1 invalid / expired / used / superseded link -> "link has expired" page (both at
    page load and at submit)
 F2 weak or breached password        -> form again with reason; link still valid
                                        until its 30 minutes run out
 F3 breach list unreachable          -> fail closed: no reset, form again; link valid
 F4 DB error in request txn          -> ROLLBACK, log; user still gets the generic
                                        message (nothing was issued, nothing leaks)
 F5 DB error in reset txn            -> ROLLBACK: token, password, sessions all unchanged;
                                        show error, link still valid
 F6 enqueue fails after COMMIT       -> log; generic message returned; the token row
                                        still counts toward the hourly limit
 F7 reset email send fails 3x        -> worker drops it silently (existing behavior);
                                        user sees nothing, re-requests (see notes)
 F8 "password changed" email lost    -> reset already complete; log only
```

## Notes

- **One table is enough.** The hourly limit is the count of rows in `password_reset_tokens` for that user in the last hour. The "one live link" rule is `used_at IS NULL`. Don't delete rows younger than 1 hour. A later cleanup job can delete rows older than that.
- **Concurrency.** `SELECT ... FOR UPDATE` on the user row makes simultaneous requests for one account line up. Without it, two requests could both pass the limit check, or both leave a live link. On submit, the conditional `UPDATE ... RETURNING` is the real "works once" guard. Two simultaneous submits can't both succeed.
- **Order of checks on submit.** The password is validated before the token is burned, so a rejected password never costs the user their link. The burn, the new hash and the session delete share one transaction, so a partial reset can't happen. Deleting the `sessions` rows logs out every device immediately, because the API checks that table on every request.
- **No account enumeration.** Unknown addresses, rate-limited accounts and real sends all return the same status and body. Do only quick DB work before responding, and let the worker do the sending. That keeps response times close for all three cases.
- **Raw token handling.** The raw token exists only in the emailed link. It also sits briefly in the queue job payload until the worker sends it, and that is unavoidable here. Don't log job payloads. Send `Referrer-Policy: no-referrer` on the reset page. The GET never changes state, so mail scanners that prefetch links won't burn the token.
- **Silent email failures (F7).** The existing worker drops failed jobs and tells nobody. A user whose reset email was dropped sees the generic message and gets no link. They can request again. A failed send still counts toward the limit of 3 per hour, so repeated failures can lock them out for up to an hour. I'm leaving the worker unchanged because the brief doesn't ask for more. The worker's failure log is the signal to alert on if this turns out to hurt.
- **Timing.** The 30-minute expiry is checked against database `now()`, not app-server clocks.
