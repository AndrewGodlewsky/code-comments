# Password reset by emailed link: design

A user who cannot log in enters their email address on "Forgot password?" and gets a one-time link that opens a page for choosing a new password. Today the web client talks to the API server. Postgres holds `users` (with the password hash) and `sessions` (one row per logged-in device, checked on every request). Mail goes through an existing email queue: the API adds a job, and an email worker sends it through a third-party mail provider. The new part is one table of reset tokens plus three API flows. The API stores only a hash of each token, so a database leak does not leak working links. The API answers every request the same way, so the form cannot be used to find out which addresses have accounts.

## Terms

- **Raw token**: 32 random bytes from a secure random generator. It appears only inside the emailed link.
- **Token hash**: the SHA-256 of the raw token. It is the only form we store.
- **Burned**: a token whose `used_at` is set, either because the reset succeeded or because a newer link replaced it. A burned token never works again.
- **Live link**: a token that is not burned and has not expired.
- **Email queue / worker**: the existing system that sends mail. The worker retries a failed send 3 times with backoff, then logs the failure and drops the job. Nobody is notified.
- **Breached-password list**: a list of known leaked passwords. The API checks the new password against it.
- **`FOR UPDATE`**: a Postgres row lock. A second transaction that wants the same row waits until the first one finishes.

## Rules

- The forgot-password endpoint always returns the same status and message: "If an account exists for that address, we've sent a link." This holds for unknown addresses (nothing is sent), rate-limited accounts and real sends.
- An account can be sent at most 3 reset emails in any rolling hour. Over the limit, the user still gets the generic message, but no link is created and no email is sent.
- A link is valid for 30 minutes after it is issued and works once.
- Issuing a new link burns any earlier live link for that account.
- The link opens a "choose a new password" page. The token is checked when the page loads and again when the form is submitted.
- A new password must be at least 12 characters and must not be on the breached list.
- A successful reset stores the new hash, burns the link, logs the account out on every device (including the one that did the reset), and sends a "your password was changed" email. The user is redirected to the login page and is not logged in automatically.

## Diagram

```
DATA (Postgres, one new table)
  password_reset_tokens
    token_hash   bytea PRIMARY KEY      -- SHA-256 of the raw token
    user_id      FK -> users
    issued_at    timestamptz
    expires_at   timestamptz            -- issued_at + 30 min
    used_at      timestamptz NULL       -- set when burned (used OR superseded)
  index (user_id, issued_at)
  Rows are kept at least 1 hour: they are the rate-limit record.

======================================================================
1. REQUEST FLOW   POST /forgot-password {email}
======================================================================

 Browser         API server                      Postgres      Email queue -> Worker -> Mail provider
    |  email        |                               |
    |-------------->|                               |
    |               | normalize email (trim, lowercase)
    |               |-- find user by email -------->|
    |               |<-- user / none ---------------|
    |               |
    |               | no user? ----------------------------> skip to response
    |               | BEGIN
    |               |-- SELECT user FOR UPDATE ---->|  (concurrent requests for
    |               |-- count tokens WHERE user_id  |   this account wait here)
    |               |   AND issued_at > now()-1h -->|
    |               |<-- n -------------------------|
    |               | n >= 3? --> ROLLBACK --------------> skip to response
    |               | raw = 32 random bytes
    |               |-- UPDATE tokens SET used_at=now()
    |               |   WHERE user_id AND used_at IS NULL   (burns earlier links)
    |               |-- INSERT (sha256(raw), user_id, now(), now()+30min) ->|
    |               | COMMIT
    |               | link = BASE_URL + "/reset?token=" + raw
    |               |-- enqueue "reset" job {to: user email, link} ---------> queue
    |               |
    |  200 "If an account exists for that address, we've sent a link."
    |<--------------|   (identical status and body on every path)
    |
    |                                              worker sends the job as given;
    |                                              fails 3x with backoff -> log, drop

======================================================================
2. LINK-CLICK FLOW   GET /reset?token=RAW   (read-only, burns nothing)
======================================================================

 Browser         API server                      Postgres
    |  GET link     |
    |-------------->|-- SELECT WHERE token_hash = sha256(RAW)
    |               |   AND used_at IS NULL AND expires_at > now() -->|
    |               |<-- row / none -----------------------------------|
    |               |
    |               | row  --> "choose a new password" page (RAW kept in the form)
    |               | none --> "this link has expired, request a new one" page,
    |               |          with a link to the /forgot-password form
    |<--------------|

======================================================================
3. SUBMIT FLOW   POST /reset {token, new_password}
======================================================================

 Browser         API server                      Postgres
    |  token + pw   |
    |-------------->|-- same token check as page load -->|
    |               |   fails --> expired page
    |               |
    |               | pw under 12 chars or on breached list
    |               |     --> form again with the reason; link stays usable
    |               | breach check errors or times out
    |               |     --> refuse (fail closed): form again, "try again"; link stays usable
    |               |
    |               | BEGIN
    |               |-- UPDATE tokens SET used_at=now()
    |               |   WHERE token_hash AND used_at IS NULL AND expires_at > now()
    |               |   RETURNING user_id ------------->|
    |               |   0 rows (lost a race) --> ROLLBACK --> expired page
    |               |-- UPDATE users SET password_hash = hash(pw) ->|
    |               |-- DELETE FROM sessions WHERE user_id -------->|  (every device,
    |               | COMMIT                                        |   incl. this one)
    |               |-- enqueue "your password was changed" job --> queue -> worker
    |  302 -> /login|
    |<--------------|   (no session created, no auto-login)

======================================================================
4. FAILURE PATHS (anything not already shown above)
======================================================================
  DB error in the request transaction
      -> ROLLBACK, log. Nothing was issued, so the user still gets the generic message.
  Enqueue fails after COMMIT
      -> log; generic message returned. The token row still counts toward the hourly limit.
  Reset email fails to send 3 times
      -> worker drops it silently (existing behaviour). The user sees nothing and
         must request again.
  DB error in the reset transaction
      -> ROLLBACK: token, password and sessions are all unchanged. Show the same form
         with "something went wrong, try again" (the user retypes the password).
         The link stays usable.
  "Password changed" email lost
      -> the reset is already complete; log only.
```

## Notes

- **One table is enough.** The hourly limit is the count of rows for that user in the last hour. "One live link" is `used_at IS NULL`. Do not delete rows younger than 1 hour; a later cleanup job can delete older ones.
- **Concurrency.** The `FOR UPDATE` lock stops two simultaneous requests for one account from both passing the limit check or both leaving a live link. On submit, the conditional `UPDATE ... RETURNING` is the real "works once" guard, so two simultaneous submits cannot both succeed.
- **Order of checks on submit.** The password is validated before the token is burned, so a rejected password never costs the user their link. The burn, the new hash and the session delete share one transaction, so a partial reset cannot happen. Deleting the `sessions` rows logs out every device at once.
- **No account enumeration.** The API does only quick database work before responding and leaves sending to the worker, so response times stay close for unknown, rate-limited and real requests.
- **Who builds the email.** The API builds the full link from a configured base URL. The job holds the recipient address and the finished link, and the worker only sends it.
- **Raw token handling.** Besides the emailed link, the raw token sits briefly in the queue job payload until the worker sends it; that cannot be avoided here. Do not log job payloads. Send `Referrer-Policy: no-referrer` on the reset page. The GET never changes state, so mail scanners that prefetch links cannot burn the token.
- **Breach check.** "Unavailable" means the check errors or times out. We refuse the reset rather than accept an unchecked password.
- **Silent email failures.** A user whose reset email was dropped sees the generic message and gets no link. A failed send still counts toward the 3 per hour, so repeated failures can lock them out for up to an hour. The worker stays unchanged because the brief does not ask for more. Its failure log is the signal to alert on if this hurts.
- **Timing.** The 30-minute expiry is checked against database `now()`, not app-server clocks.

## Open questions

- Where the breached-password list lives (local file or outside service) is not in the brief, so the design does not decide it. It only needs a check that can succeed, fail or be unavailable.