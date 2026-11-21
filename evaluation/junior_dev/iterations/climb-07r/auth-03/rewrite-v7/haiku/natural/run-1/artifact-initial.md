# Password reset by emailed link: design

## Summary

Three flows: request (POST /password-reset), link open (GET check on page load), and submit (POST /password-reset/complete). Reset state lives in one new table, `password_reset_tokens`. Mail goes through the existing email queue. The only other changes are the password update and session deletion on success.

## Data

```
password_reset_tokens
  id          bigint        primary key
  user_id     bigint        not null, references users, indexed
  token_hash  bytea(32)     unique; SHA-256 of the raw token
  created_at  timestamptz   not null
  expires_at  timestamptz   not null          -- created_at + 30 min
  used_at     timestamptz   null              -- set when the reset succeeds
  revoked_at  timestamptz   null              -- set when a newer link replaces it
```

- A token is active when `used_at` and `revoked_at` are both null and `expires_at > now()`.
- Rate limit: count rows for the user with `created_at > now() - 60 min`. A cleanup job deletes rows with `created_at < now() - 60 min`. That keeps exactly the window the cap needs and keeps the table small.
- Not stored: the raw token, the email address, the IP address.
- Existing tables: `users.password_hash` is overwritten on success, and `sessions` rows for the user are deleted on success. No other schema change.

## Diagram

```
REQUEST: POST /password-reset  {email}

Browser            API                                        Postgres / email queue
-------            ---                                        ----------------------
 submit ---------> normalise email (trim, lowercase)
                   SELECT user WHERE email = ? ---------------> users
                     |
                     +-- no user --------------------------------------+
                     |                                                |
                     +-- user found                                   |
                         BEGIN                                        |
                         SELECT user FOR UPDATE --------------------> users   (row lock per account)
                         count tokens with created_at > now()-60m --> password_reset_tokens
                           |
                           +-- count >= 3 -------------------------+   |
                           |                                       |   |
                           +-- count < 3                           |   |
                               UPDATE tokens SET revoked_at        |   |
                                 WHERE user_id = ? AND active ---> password_reset_tokens
                               INSERT token (hash, expires +30m) -> password_reset_tokens
                               INSERT email job (link, encrypted) -> email queue
                               COMMIT                              |   |
                                                                   v   v
 <-- 200 "If an account exists for that address, we've sent a link."   (same body on every branch)


EMAIL WORKER (async, after the request has already returned)

 queue job --> worker --> mail provider
                 |
                 +-- sent:            mark job done, delete payload
                 +-- failed:          retry with backoff, up to 3 times
                 +-- failed 3 times:  log job id and user id (never the link),
                                      drop job, raise alert. Nobody is told.


LINK OPEN: GET /reset?token=T  (page loads, then the API checks T)

Browser                          API                              Postgres
-------                          ---                              --------
 open link -----------------> sha256(T) -> hash
 (page reads T once, then     SELECT token WHERE token_hash = ? -> password_reset_tokens
  removes it from the URL)      |
                                +-- missing, used, revoked or expired
 <-- "This link has expired. Request a new one."
                                +-- active
 <-- form: new password, with T held in a hidden field


SUBMIT: POST /password-reset/complete  {token T, new_password}

Browser                          API                              Postgres
-------                          ---                              --------
 submit form ---------------> sha256(T), read token (as above)
                                |
                                +-- not active --> expired page (password is not checked)
                                |
                              validate new_password (no DB):
                                length >= 12; not on breached list (in-process list)
                                |
                                +-- rejected --> 422 with reason. Token untouched,
                                |                form stays, user may retry until expiry.
                                |
                              pw_hash = hash(new_password)     (outside the transaction)
                              BEGIN
                              SELECT token FOR UPDATE -------> password_reset_tokens
                                |
                                +-- no longer active (second tab, race) --> ROLLBACK
                                |        <-- expired page
                                +-- active
                                     UPDATE users SET password_hash ----> users
                                     UPDATE tokens SET used_at = now() -> password_reset_tokens
                                     UPDATE tokens SET used_at = now()    (all of the user's
                                       WHERE user_id = ? AND used_at IS NULL   open tokens)
                                     DELETE sessions WHERE user_id = ? ---> sessions
                                     INSERT email job ("password changed") -> email queue
                                     COMMIT
 <-- 302 redirect to /login   (no session cookie is set, so no auto-login)
```

## Notes

1. **Token.** Generate 32 bytes from a CSPRNG and base64url-encode them for the link (43 characters). Store only the SHA-256 digest. Lookup goes through the unique index on the hash, so raw tokens are never compared.
2. **One active link.** The request transaction revokes unused tokens before inserting the new one. It takes the user row lock first, and that lock also serialises the rate-limit count, so two concurrent requests cannot both see a count of 2 and both proceed.
3. **Same transaction for the link and the job.** If the link row commits but the email job is lost, the user holds a link they never receive. If the queue lives in Postgres, enqueue in the same transaction. Otherwise write an outbox row in the same transaction and have a relay drain it.
4. **The raw token reaches the queue.** The worker needs the link, so the job payload contains the token. Encrypt the payload at rest, delete it when the job is sent or dropped, and keep it out of logs and any job dashboard. Anyone who reads an unsent job could use that link for up to 30 minutes.
5. **Unknown-address timing.** The unknown branch does one indexed read and returns. The known branch also writes and commits. Keep the gap small by returning after commit, and consider a fixed minimum response time. Email send time is never on the request path.
6. **Burn is atomic.** The password update, token `used_at`, session deletion and the notice job commit together. A failure rolls all of them back, so the link still works and the user can retry.
7. **Check order on submit.** Token first, then password. An expired link never reveals password rules, and a rejected password never touches the token row.
8. **Breached list.** Load it into memory at startup. No network call happens in the request path. Use the same normalisation when matching as when the list was built.
9. **Hash outside the transaction.** Hashing the new password before `BEGIN` keeps the row lock short. The lock covers only the recheck and the writes.
10. **Logout everywhere.** Deleting the `sessions` rows takes effect on the next request, because the API checks sessions on every request. That includes the device that did the reset. Any other long-lived credential (refresh tokens, remember-me, API keys) must be revoked in the same transaction. The brief does not mention one, so confirm.
11. **Token in the URL.** The token is in the query string on the first load only. Send `Referrer-Policy: no-referrer` on reset pages, keep the query string out of access logs, and remove it from the address bar after load. The submit request carries the token in the body.

## Failure paths

| Path | User sees | Stored state |
|---|---|---|
| Unknown email | generic message, no email | nothing written |
| Over 3 links in the rolling hour | generic message, no email | nothing written |
| Email send fails 3 times | generic message; no email arrives | token exists, never used, expires; job dropped and logged |
| Link missing, used, revoked or expired on open | expired page | nothing written |
| Link expires between open and submit | expired page | nothing written |
| Password under 12 characters, or breached | 422 with reason; form stays | nothing written; link still usable |
| Two submits race on one link | one succeeds; the other gets the expired page | row lock; one commit |
| Database error during submit | error page; user retries | rolled back; link still valid |
| "Password changed" email fails after reset | nothing; reset stands | job dropped and logged |
| Reset from a device that is logged in | redirect to login | that device's session row is deleted; it logs out |

## Open questions

- **Silent send failure.** The user is told "we've sent a link" and nothing arrives. Decide whether drops raise an ops alert (recommended), whether support can see the drop log, and whether a "didn't get it?" path is needed.
- **No throttle beyond the per-account cap.** The request endpoint has no per-IP or global limit. Each address gets at most 3 links an hour, but many addresses can still drive mail volume. The brief does not cover this, so confirm whether to add it.
- **Other credentials.** Revoke refresh tokens or any other credential that lives outside `sessions`, if they exist.
- **Breached list.** Confirm its source and update cadence.
- **Email normalisation.** Confirm whether `users.email` is stored lowercase or needs a `lower()` index for the lookup.