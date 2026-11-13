# Password reset by emailed link: design

## Diagram

```
PASSWORD RESET BY EMAILED LINK

Parties:  BROWSER = web client    API = API server    DB = Postgres
          QUEUE = email queue     WORKER = email worker    MAIL = mail provider


=== A. REQUEST  POST /password-reset  { email } ==============================

  BROWSER --- email ---> API
                          |
                          | 1. normalise email (trim, lowercase); look up users.email
                          |
                          +-- no such user -----------------------------------+
                          |                                                   |
                          | 2. BEGIN                                          |
                          |    SELECT ... FROM users WHERE id = ? FOR UPDATE  |
                          |    (serialises concurrent requests per account)   |
                          | 3. SELECT count(*) FROM password_resets           |
                          |      WHERE user_id = ? AND issued_at > now()-1h   |
                          |                                                   |
                          +-- count >= 3 -> COMMIT, no writes ----------------+
                          |                                                   |
                          | 4. UPDATE password_resets SET state='revoked'     |
                          |      WHERE user_id = ? AND state='active'         |
                          |    INSERT row: token_hash, state='active',        |
                          |      expires_at = now() + 30 min                  |
                          | 5. INSERT outbox/queue job: reset email with link |
                          |    (same transaction)                             |
                          | 6. COMMIT                                         |
                          |                                                   |
                          v                                                   v
                  200 "If an account exists for that address,       (same response)
                       we've sent a link."   <-------------------------------+


=== B. OPEN LINK  GET /reset/{token}   (read only, never consumes the link) ====

  BROWSER --- GET ---> API --- SHA-256(token) ---> DB
                        |                           SELECT FROM password_resets
                        |                           WHERE token_hash = ?
                        |                             AND state = 'active'
                        |                             AND expires_at > now()
                        |
                        +-- row found ---> 200 "choose a new password" form
                        |                  (token carried in a hidden field)
                        |
                        +-- not found, used, revoked or expired
                                           ---> 200 "this link has expired,
                                                     request a new one"
                                           (same page for all four cases)


=== C. SUBMIT  POST /reset  { token, new_password } ===========================

  BROWSER --- POST ---> API
                         |
                         | 1. check token as in B. Invalid -> "expired" page. Stop.
                         |
                         | 2. check password:
                         |      length >= 12 AND not on breached list (local list)
                         |      rejected -> re-render form with error.
                         |      No writes. Link stays active until it expires.
                         |
                         | 3. hash new password (argon2id), outside the transaction
                         |
                         | 4. BEGIN
                         |      SELECT ... FROM password_resets
                         |        WHERE token_hash = ? FOR UPDATE
                         |      re-check state='active' AND expires_at > now()
                         |        fails -> ROLLBACK -> "expired" page
                         |      UPDATE password_resets
                         |        SET state='used', used_at = now()
                         |      UPDATE users SET password_hash = <new>
                         |      DELETE FROM sessions WHERE user_id = ?   (all devices)
                         |      INSERT job: "your password was changed" email
                         |    COMMIT
                         |
                         v
                  302 redirect -> /login        (no session is created)


=== D. FAILURE PATHS ==========================================================

  D1  unknown email          generic 200. No row, no email, no queue job.
  D2  over 3 per rolling h   generic 200. No new row, no revoke (the existing
                             active link stays valid), no email.
  D3  mail send fails        WORKER retries 3 times with backoff, then logs and
                             drops the job. Nobody is notified. The link exists
                             but was never delivered; it expires in 30 min.
                             The user sees the generic message and may retry.
  D4  older job still queued WORKER re-checks state='active' before sending.
                             Skips the send if the link was revoked.
  D5  double submit / race   FOR UPDATE serialises. The second submit finds
                             state='used' and gets the "expired" page.
  D6  weak or breached pw    form error. Link untouched and still usable.
  D7  link expires mid-form  submit finds expires_at passed -> "expired" page.
                             Nothing written.
  D8  API crashes mid-txn    rollback. No link issued, no job queued.
  D9  API crashes after COMMIT  the job was written in the same transaction,
                             so the relay still sends it.


=== DATA ======================================================================

  password_resets
    id           PK
    user_id      FK -> users.id
    token_hash   BYTEA(32), UNIQUE          SHA-256 of the raw token
    state        ENUM('active','used','revoked')
    issued_at    timestamptz (DB clock)
    expires_at   timestamptz = issued_at + 30 min
    used_at      timestamptz NULL
    index (user_id, issued_at)              serves the rate-limit count

  Not stored: the raw token, the email address copy, the password.
  Retention: delete rows older than 24 h. Keep at least 1 h for the rate window.
```

## Notes

- **Token.** 32 bytes from a CSPRNG, base64url-encoded into the link. Only the SHA-256 hash is stored. The hash is looked up through the unique index. Because the token has 256 bits of entropy, a plain hash with no salt is enough.
- **Clock.** All expiry and rate-window checks use the database `now()`, so app-server clock skew does not matter.
- **Rate limit atomicity.** Locking the user row before counting prevents two concurrent requests from both seeing a count of 2. The limit counts issued links, not requests. Unknown addresses create no rows, so they never count.
- **Enumeration and timing.** Every branch returns the same body and status. Email is sent asynchronously, so response time does not depend on the mail provider. For the unknown-address branch, consider a fixed minimum response delay so the timing matches the known-address branch.
- **Link previewers.** The GET in B never consumes the link. Mail-scanner prefetches therefore cannot burn it.
- **Token in the URL.** The token shows up in access logs, browser history and Referer headers. Strip the token from logs. Send `Referrer-Policy: no-referrer` on the reset pages, and load no third-party scripts there. The token is then carried in the POST body on submit.
- **Logging out every device.** The API checks `sessions` on every request, so deleting the rows takes effect immediately. If session data is cached anywhere, invalidate that cache in the same step.
- **Outbox.** Both emails are written in the same transaction as the state change, so a job exists exactly when the change committed. If the queue is not in Postgres, write an outbox row in the transaction and have a relay enqueue it.
- **Queue payload.** The reset email job holds the rendered link, so the raw token sits in queue storage until the send completes. Treat the queue as sensitive: redact it from logs and delete the job on completion. An alternative is to have the worker generate the token at send time. That makes the hash and the send race with each other, so it is not recommended.

## Open decisions for review

1. **Silent drop after 3 failed sends.** The spec says nobody is notified, but the user then burns one of their 3 hourly slots for an email that never arrived. Recommended: the worker writes a `send_status` column to `password_resets`, and ops alerts on the failure rate. This is visibility for ops, not a user notification.
2. **Failed sends count toward the quota.** Counting issued links is the simplest rule, and it protects the mail provider from abuse. The alternative is to count only delivered links, which needs a delivery-status write from the worker.
3. **Breached-password check.** Use a local list. An online lookup service would expose the candidate password.
4. **Attempt cap on a link.** The spec allows unlimited retries until expiry. Because the token is 256 bits, brute force against the token is not a practical risk. Confirm that unlimited password retries on one link are acceptable.
