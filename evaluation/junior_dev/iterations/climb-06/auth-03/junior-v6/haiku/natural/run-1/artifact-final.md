# Design: password reset by emailed link

## Summary

A user who cannot log in enters their email on a "Forgot password?" form. The system sends a one-time link that is valid for 30 minutes. The link opens a page where the user chooses a new password. A successful reset logs the user out on every device and sends a "your password was changed" email. The change adds one table, three API endpoints, one page and two emails. Login and the session rules are unchanged. The mail worker's retry policy is unchanged, but the worker gets one new check before it sends a reset email.

**How the system works today.** The web client calls the API server. Postgres holds `users`, which includes each password hash, and `sessions`, which has one row per logged-in device. The API checks a session on every request. Outgoing mail goes through an email queue. The API adds a job, and a worker sends it through the third-party mail provider. If a send fails, the worker retries up to 3 times with backoff. Then it logs the failure and drops the job. Nobody is told.

**Assumption.** This design treats the email queue as a Postgres table, `email_jobs`. Open question 1 covers the case where it is not.

## Terms

- **Token**: 32 random bytes from a secure random generator, written as text. The raw token appears only inside the reset link.
- **Token hash**: the SHA-256 of the token. The database stores only the hash.
- **Link**: `https://<app>/reset#<token>`. The part after `#` is the fragment. Browsers never send it to the server, so it stays out of server logs and referrers.
- **Live link**: a token that is not used, not superseded and not past its expiry. The one test for "live" is `used_at IS NULL AND superseded_at IS NULL AND expires_at > now()`.
- **Supersede**: when a new link is issued, older live links for the same account are marked with `superseded_at`. They stop working.
- **Burn**: mark a link as used (`used_at`), so it cannot be used again.
- **Job**: a row in `email_jobs` that asks the worker to send one email.
- **Worker**: a background process that takes jobs from the queue and sends them through the mail provider.
- **Transaction**: database writes that all succeed together or not at all. COMMIT keeps them. ROLLBACK undoes them.
- **Row lock (`FOR UPDATE`)**: holds the user's row, so two requests for the same account cannot count and issue at the same time.
- **Rate window**: the last 60 minutes, counted on a rolling basis.
- **Normalised email**: the form in which the app already stores email addresses. Lookups use it.
- **Breached-password list**: a copy of known leaked passwords, held on our side. The password is never sent to a third party to be checked.
- **Generic message**: "If an account exists for that address, we've sent a link." The request endpoint returns it every time, whether or not the account exists.

## 1. Request flow

The user submits their email. The API either issues a link and queues an email, or does nothing. The reply is the same message in both cases.

```
Client          API                        Postgres                 Worker       Provider
  |               |                            |                       |             |
  |-- POST ------>|                            |                       |             |
  |               |-- BEGIN; SELECT user ----->|                       |             |
  |               |   FOR UPDATE               |                       |             |
  |               |<-- user, or none ----------|                       |             |
  |               |                            |                       |             |
  |               |  no user:  COMMIT -------->|   nothing queued      |             |
  |<-- generic ---|                            |                       |             |
  |               |                            |                       |             |
  |               |-- COUNT tokens, 60 min --->|                       |             |
  |               |<-- N ----------------------|                       |             |
  |               |  N >= 3:   COMMIT -------->|   no link, no email   |             |
  |<-- generic ---|                            |                       |             |
  |               |                            |                       |             |
  |               |  N < 3:  supersede live links;                     |             |
  |               |          INSERT token row; INSERT reset job ------>|             |
  |               |-- COMMIT ----------------->|                       |             |
  |<-- generic ---|  (padded to fixed minimum) |                       |             |
  |               |                            |<-- claim job ---------|             |
  |               |                            |--- job row ---------->|             |
  |               |                            |                       |-- send ---->|
  |               |                            |                       |<-- 250 OK --|
  |               |                            |<-- delete job --------|             |
```

Steps:

1. **Starts** when the form posts `{email}` to `POST /api/password-reset/request`. The API opens a transaction and reads the user row by normalised email, with `FOR UPDATE`. If there is no user, it commits and returns the generic message. Nothing is inserted and no job is queued. The row lock makes the count in step 2 exact when requests arrive at the same time.
2. **Count** every token row for this user created in the last 60 minutes, in any state (live, used, superseded or expired). Each row is one reset email that was sent or queued, and the limit is on emails. If the count is 3 or more, the API commits and returns the generic message. No link is created and no email is sent. The user is not told why.
3. **Issue** otherwise, in the same transaction. Mark the user's live links with `superseded_at = now()`. Insert a token row with the token hash, `created_at`, and `expires_at` set to 30 minutes after creation. Insert a reset job. The job holds the user id, the recipient address (the normalised email from step 1) and the raw token.
4. **Reply.** Commit, then return the generic message. The reply waits until the fixed minimum time has passed (see notes).
5. **Send.** The worker claims the reset job, sends it and deletes it. Section 3 covers the details.

**What keeps the data.** `password_reset_tokens` keeps only the token hash. `email_jobs` keeps the raw token until the job is sent or dropped.

**Why it is built this way.**
- Everything in steps 1 to 4 runs in one transaction. The old link dies in the same commit that creates the new one. If the job insert fails, everything rolls back and the old link stays live. This works only because the queue is a Postgres table (open question 1).
- The raw token is 32 bytes from a secure random generator, encoded as base64url. It goes into the job and nowhere else.
- Unknown addresses skip the insert and the job, so they finish faster. To hide this, `/request` alone is padded to a fixed minimum time that is above its slowest path. The padding waits after COMMIT, so the row lock is already released. `/check` and `/complete` are not padded, because they do not reveal whether an account exists.

## 2. Link click and submit

The user clicks the link. The reset page checks the token. The user then submits a new password. Both checks run on the server. The page script decides what to show after the check.

```
Client          API                          Postgres
  |               |                              |
  | open https://<app>/reset#<token>             |
  | script reads token, clears fragment          |
  |-- POST /check {token} ->                     |
  |               |-- SELECT by token_hash ----->|
  |               |<-- row or none --------------|
  |<-- {valid} ---|   read only, burns nothing   |
  |               |                              |
  | valid true: show form; valid false: show expired page
  |               |                              |
  |-- POST /complete {token, password} ->        |
  |               |-- 1. read: live? if not, 410 |   stop, nothing written
  |               |-- 2. password check (local, no database)
  |               |      weak or breached: 422, stop
  |               |-- 3. BEGIN; UPDATE token SET used_at WHERE live RETURNING user_id ->|
  |               |<-- 1 row, or 0 rows ---------|
  |               |      0 rows: ROLLBACK, 410   |
  |               |      1 row: continue         |
  |               |-- 4. UPDATE users SET password_hash ->|
  |               |-- 5. DELETE sessions WHERE user_id ->|
  |               |-- 6. INSERT changed-password job ->|
  |               |-- COMMIT ------------------->|
  |<-- 303 /login-|                              |
  |               |                              |
  |               |  DB error before COMMIT: ROLLBACK, 500; link stays live
```

Steps:

1. **Load.** The user clicks the link and the reset page loads. Its script reads the token from the fragment into memory and clears the fragment with `history.replaceState`. The page sets `Referrer-Policy: no-referrer`.
2. **Check.** The script posts the token in the body to `POST /api/password-reset/check`. The token is in the body, not in a query string, so it does not reach logs that way. The check is read-only. It burns nothing and returns `{valid: true|false}`.
3. **Show.** If `valid` is true, the script shows the "choose a new password" form. If it is false, the script shows the expired page: "this link has expired, request a new one." The server does not make this choice. The page gives no reason. Expired, used and superseded links all look the same.
4. **Submit.** The user posts `{token, password}` to `POST /api/password-reset/complete`. The server does these things in order.
   - a. **Read.** If the token is not live, return 410 `{error: "expired"}`. Nothing is written. This is only a fast exit. Two submits can both pass it at the same moment, so it does not guard against a race.
   - b. **Check the password.** It must be at least 12 characters and at most 128 (a cap that bounds hashing cost). It must not be on the breached list. If it fails, return 422 `{error: "weak"}` or `{error: "breached"}`. Nothing is written, and the link stays live until it expires.
   - c. **Burn.** Open a transaction. Run a conditional update that sets `used_at = now()` only where the token is live. It returns the `user_id`. This is the real guard. If zero rows come back, another submit won the race, or the link has expired. Roll back and return 410.
   - d. **Reset.** With one row back, store the new password hash on `users`. Delete every `sessions` row for that user. This logs the user out on every device, including the one that did the reset. Insert a "password changed" job that holds only the user id.
   - e. **Finish.** Commit and return 303 to `/login`. The user is not logged in.
5. **Database error.** If the database fails before COMMIT, roll back. The password, the sessions and the link stay as they were, and the link is still live. Return 500. The page shows "Something went wrong, please try again" and keeps the form open. The user can submit again while the link is within its 30 minutes.

**What keeps the data.** `users` changes only `password_hash`. `sessions` loses the user's rows. `password_reset_tokens` gets `used_at`.

**Why it is built this way.**
- The reset link's fragment never reaches the server, so the token stays out of logs and referrers.
- Submit checks twice. The read is a quick exit. The conditional update is what keeps two submits from both succeeding.
- A session is one row per logged-in device, and the API checks it on every request. Deleting every row for the user logs them out everywhere. No session is created during the reset.
- The password is checked against a local list. It is never sent to a third party.

## 3. Reset email worker

The worker sends queued emails. For a reset job, it checks that the link is still live before it sends anything.

Steps:

1. **Claim.** The worker claims a job from `email_jobs` with `FOR UPDATE SKIP LOCKED`. Two workers never claim the same job.
2. **Check (reset job only).** Hash the raw token in the job and find the token row by `token_hash`, which has a unique index. Apply the live test. If the row is missing or not live, delete the job without sending it, and log at info. This stops an old link from being sent after a newer one has been issued, or after 30 minutes have passed.
3. **Build and send.** Build `https://<app>/reset#<token>` from the raw token and the app's base URL setting. Send it to the recipient address in the job. The worker does not look up anything else.
4. **Success.** On a 2xx reply from the provider, delete the job row. This also removes the raw token.
5. **Failure.** Retry with backoff under the existing policy, up to 3 times. If it still fails, log an error and delete the job. Nobody is told. Retries send the same token, so they do not count against the hourly limit.
6. **Changed-password job.** This job holds only a user id, so there is no live check. Send "your password was changed" with the same retry and drop rules. When it is dropped, log it with the user id.

Notes:
- If the worker crashes after the provider accepts the email but before it deletes the job, the job runs again. The same link is sent twice. The link is single-use, so the second copy is harmless.
- If the worker crashes while it holds a claim, the existing queue decides when the claim is released (open question 6).

## 4. Token lifecycle

A token is issued, and then it ends in one of three final states. Only the issued state is live.

```
                  issue (under the 3-per-hour limit)
                                |
                                v
               +-----------------------------+
               |  ISSUED  (the only live)    |
               |  used_at null               |
               |  superseded_at null         |
               +-----------------------------+
                 |          |           |
   30 min pass   |          |           |  new link issued for same account
   (time check,  |          |           |
    no write)    v          |           v
          +-----------+     |     +----------------+
          |  EXPIRED  |     |     |  SUPERSEDED    |
          +-----------+     |     |  superseded_at |
                            |     +----------------+
                            |
             successful reset commits
                            v
               +-----------------------------+
               |  USED   used_at = now()     |
               +-----------------------------+
```

Notes:
- Only ISSUED is live. USED and SUPERSEDED are final. EXPIRED needs no write, because the time check is enough.
- The check, the submit and the worker all use the same live test. That keeps the rule in one place.

## 5. What happens when things fail

| Where | What happens | What the user sees |
|---|---|---|
| `/request`, address has no account | Nothing inserted, nothing sent | Generic message, same timing |
| `/request`, account has 3 or more token rows in the last 60 minutes | No link, no email. Commit. | Generic message. Not told why. |
| `/request`, database error before COMMIT | Everything rolls back. The old link stays live. | Not defined by the brief (open question 8) |
| Worker, provider keeps failing after 3 retries | Job deleted, error logged | Screen said "sent" but no email came. The user requests again, and that request counts toward the limit. Metric needed (open question 3). |
| Worker, link superseded or expired when the job runs | Job deleted without sending. Logged at info. | No email arrives. Only the newest link works. |
| Worker, crash after provider accepts, before delete | Job runs again | The same link arrives twice. Harmless, since the link is single-use. |
| `/check` or `/complete`, link expired, used or superseded | `/check` returns `valid: false`. `/complete` returns 410. | Expired page: "this link has expired, request a new one" |
| `/complete`, password under 12 characters, on the breached list or over 128 | Nothing written | 422 form error. The link still works until it expires. |
| `/complete`, two submits race | One burns the link. The other gets zero rows and rolls back. | The second gets the expired page (410). |
| `/complete`, database error before COMMIT | Token, password and sessions stay unchanged | "Something went wrong, please try again". The form stays open. The user can resubmit within 30 minutes. |
| Changed-password email, dropped after retries | Job deleted, logged with the user id | Nobody is told. Alert on the count (open question 3). |

## 6. Data

- **`password_reset_tokens`** (new table):
  - `id`
  - `user_id` (foreign key, not null)
  - `token_hash` (unique, not null, SHA-256 of the raw token)
  - `created_at`
  - `expires_at` (created plus 30 minutes)
  - `used_at` (nullable)
  - `superseded_at` (nullable)
  - An index on `(user_id, created_at)` serves the rate-limit count. This table never stores the raw token, an IP address or a user agent.
- **Retention.** A scheduled delete removes rows older than 24 hours. The rate limit needs only the last hour. The purge does not touch `email_jobs`. The worker deletes the jobs it drops (open question 7 covers the scheduler).
- **`email_jobs`.** A reset job holds the user id, the recipient address and the raw token until it is sent or dropped, and then its row is deleted. A changed-password job holds only the user id. The queue is access-controlled like other job payloads.
- **Conflict with the brief.** The brief says the raw token is never stored, except inside the link. This design keeps it in the reset job until it is sent or dropped. Open question 2 covers this.
- **`users`.** Only `password_hash` changes.
- **`sessions`.** Rows for the user are deleted on a successful reset.

## Build and rollout

This document covers how the system runs. Build order and rollout are not covered here. Resolve open questions 1, 4, 5, 6 and 7 before building.

## Open questions

1. **Queue location.** If the queue is Postgres, the job insert shares the transaction, as drawn. If it is external, enqueue after COMMIT instead. A crash between COMMIT and enqueue leaves a superseded or unused token that nobody holds, so the cost is a user who must request again. Confirm the location before implementation.
2. **Raw token at rest in the job.** It lives only until the job is sent or dropped. If that is not acceptable, encrypt the payload with a key that only the worker holds. Decision needed.
3. **Alerting.** Dropped reset jobs and dropped changed-password jobs should each emit a metric. The brief does not require this, but without it these failures are invisible.
4. **Password maximum length.** The brief sets only a minimum. This design suggests 128 to bound hashing cost. Decision needed.
5. **Response padding.** The fixed minimum needs a measured value, taken from the slowest real `/request` path. It has not been measured yet.
6. **Claim release after a crash.** The brief does not say when a claimed job is released after a worker dies mid-send, or whether it runs again. The existing queue decides this. Confirm before implementation. A repeat send is harmless. A job that never runs leaves the user without an email, and its raw token stays in `email_jobs` until the job runs or is removed.
7. **Purge schedule.** The 24-hour purge needs a scheduler. Confirm which existing scheduled job runs the delete, and how often.
8. **Reply when `/request` fails.** The brief does not say what the user sees if the request fails before COMMIT. Decide before implementation.