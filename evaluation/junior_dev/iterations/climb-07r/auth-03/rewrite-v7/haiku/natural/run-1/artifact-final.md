# Password reset by emailed link: design

## Summary

A user who cannot log in enters their email on a "Forgot password?" form. If the account exists and is under its limit, the API saves a one-time link that expires 30 minutes after it is issued, and it queues an email with that link. The link opens a page where the user picks a new password. On success the password changes, every unused link and every session for the account ends, and the user is sent to the login page. Each step checks the database again, so a link works once even when two requests race.

Today the web client calls the API, which reads and writes Postgres. Mail already goes through an email queue: the API adds a job, and a worker sends it through our third-party mail provider, retrying up to 3 times with backoff. After 3 failed tries the worker logs the failure and drops the job, and nobody is told.

## Terms

- **Postgres**: our database. It holds every table named here.
- **users**: the table of accounts. Each row holds the account's password hash.
- **Password hash**: a one-way scrambled form of a password. We store this, never the password.
- **sessions**: the table with one row per logged-in device. The API checks it on every request, so deleting a row logs that device out.
- **Email queue and worker**: the API adds an email job to the queue. The worker takes jobs from the queue and sends them.
- **Token**: 32 random bytes. It appears only inside the link.
- **SHA-256 hash**: a fixed one-way fingerprint of the token. We store the fingerprint, so the raw token is never stored.
- **Burn**: mark a link as used so it can never work again.
- **Revoke**: mark a link as replaced by a newer link.
- **Rolling hour**: the 60 minutes before now. The window moves with every request.
- **Row lock**: a lock on one database row. Other transactions that need the row wait until it is released, so they run one after another.
- **Breached-password list**: passwords that have appeared in known data leaks. We refuse them.

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

## Steps

Each step shows what starts it, what it does, and what it keeps. The table under "What happens when things fail" gives the user-facing outcome of each failure.

1. **Request.** Starts when a user submits their email on the form. The API trims and lowercases the address, then looks up the account.
   - Unknown address: return the generic message. Nothing is written and nothing is sent.
   - Known address: lock the account's row, then count this account's token rows created in the rolling hour. Every request counts, even if the link was later used or revoked.
   - Count of 3 or more: return the generic message. Nothing is written and no email is sent.
   - Count under 3: revoke any unused link for the account, save the new token's hash with an expiry 30 minutes from now, and queue an email job that holds the link. Commit, then return the generic message.
   - The generic message is always "If an account exists for that address, we've sent a link."
   - Why the lock: two requests at the same time cannot both see a count of 2 and both go ahead.
   - Keeps: a `password_reset_tokens` row with the hash and times. The raw token exists only in the email job until the job is sent or dropped.
   - If the database fails, the transaction rolls back and nothing is sent.

2. **Email worker.** Starts when a new email job is in the queue. The worker sends the job through the mail provider. Sending never happens on the request path.
   - Sent: mark the job done and delete its payload.
   - Failed: retry with backoff, up to 3 times.
   - Failed 3 times: log the job id and user id, never the link. Drop the job and raise an alert. Nobody tells the user. The link stays unused and expires on its own after 30 minutes.
   - Keeps: the job payload holds the raw token until the job is sent or dropped. It is encrypted at rest and kept out of logs and any job dashboard. Anyone who reads an unsent job could use that link for up to 30 minutes.

3. **Link open.** Starts when the user clicks the link, `GET /reset?token=T`. The page reads T once and removes it from the address bar. The API hashes T and looks up the hash.
   - Missing, used, revoked or expired: show "This link has expired. Request a new one." Nothing is written.
   - Active: show the "choose a new password" form, with T in a hidden field. Nothing is written.
   - Keeps: nothing is stored. The raw token lives only in the page's hidden field.

4. **Submit.** Starts when the user submits the form: `POST /password-reset/complete` with `{token T, new_password}`. The API checks in this order, and a failed check stops the request:
   1. **Token.** Hash T and read the row. If it is not active, show the expired page. The password is not checked, so an expired link never reveals password rules.
   2. **Password.** Check that it has at least 12 characters and is not on the breached-password list. The list is in memory. If it fails, return 422 with the reason. The form stays and the token is untouched, so the user can retry until the link expires.
   3. **Hash.** Hash the new password before the transaction. This keeps the row lock short.
   4. **Transaction.** Begin, lock the token row, and check again that it is active. If it is not (a second tab, or a race), roll back and show the expired page.
   5. **Burn.** If still active, in the same transaction: save the new password hash to `users`, set `used_at` on this token, set `used_at` on all of the user's other unused tokens, delete all of the user's `sessions` rows (including the device that made the reset), and queue the "your password was changed" email. Commit.
   6. **Redirect.** Return a 302 to `/login`. Set no session cookie, so the user is not logged in automatically.
   - Keeps: `users.password_hash` and the `sessions` rows change only on success.
   - Burn is atomic. The password update, `used_at`, session deletion and notice job commit together. If any part fails, all of it rolls back and the link still works.

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
- Rate limit: count the user's rows with `created_at > now() - 60 min`. The cleanup job deletes rows with `created_at < now() - 60 min`. That keeps exactly the window the cap needs and keeps the table small.
- Not stored: the raw token, the email address, the IP address.
- Existing tables: `users.password_hash` is overwritten on success, and the user's `sessions` rows are deleted on success. No other schema change.

## What happens when things fail

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

## Rules that apply across steps

- **Token.** Generate 32 bytes from a cryptographically secure random generator and base64url-encode them for the link (43 characters). Store only the SHA-256 digest. Lookup uses the unique index on the hash, so raw tokens are never compared.
- **Link and job together.** The link row and the email job must commit in one transaction. Otherwise the user could hold a link they never receive. If the queue lives in Postgres, enqueue in that transaction. If not, write an outbox row (a row that records a pending email) in the same transaction, and a relay process moves it to the queue.
- **Timing.** An unknown address does one indexed read and returns. A known address also writes and commits. To keep the gap small, return only after commit, and consider a fixed minimum response time.
- **Breached list.** Load it into memory at startup. No network call happens during a request. Normalise passwords the same way when matching as when the list was built.
- **Browser.** Reset pages send `Referrer-Policy: no-referrer`. The query string stays out of access logs. The page removes the token from the address bar after load. The submit request carries the token in the body, not the URL.
- **Logout everywhere.** Deleting session rows takes effect on the next request, because the API checks sessions on every request. That includes the device that made the reset.

## Build notes

- Schema changes are listed under Data. Add the `password_reset_tokens` table with its indexes.
- Add the cleanup job that deletes token rows older than 60 minutes.
- Load the breached-password list at startup.

## Open questions

- **Silent send failure.** The user is told "we've sent a link" and nothing arrives. Decide whether drops raise an ops alert (recommended), whether support can see the drop log, and whether a "didn't get it?" path is needed.
- **No throttle beyond the per-account cap.** The request endpoint has no per-IP or global limit. Each address gets at most 3 links an hour, but many addresses can still drive mail volume. The brief does not cover this, so confirm whether to add one.
- **Other credentials.** Confirm whether refresh tokens, remember-me cookies or API keys exist outside `sessions`. If they do, revoke them in the same transaction as the reset.
- **Breached list.** Confirm its source and how often it is updated.
- **Email normalisation.** Confirm whether `users.email` is stored lowercase, or whether the lookup needs a `lower()` index.
- **Password-changed email address.** The brief does not say whether the notice job carries the address or the worker looks it up in `users`.