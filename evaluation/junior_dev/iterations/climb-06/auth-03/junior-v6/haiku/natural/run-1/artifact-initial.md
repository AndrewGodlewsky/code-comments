# Design: password reset by emailed link

Users who cannot log in enter their email on a "Forgot password?" form and get a single-use link valid for 30 minutes. The link opens a "choose a new password" page. Nothing new is added to login, sessions or the mail worker's retry rules. The change is one table, three endpoints, one page and one email template.

Endpoints:

- `POST /api/password-reset/request` with `{email}` always returns the same generic 200 body.
- `POST /api/password-reset/check` with `{token}` returns `{valid: true|false}` and burns nothing.
- `POST /api/password-reset/complete` with `{token, password}` returns 303 to `/login` on success, 410 `{error: "expired"}` for a dead link, or 422 `{error: "weak"|"breached"}` for a rejected password (the link stays live).

## 1. Request flow

```
Client          API               Postgres            Worker         Provider
   |-- POST ----->|                 |                   |               |
   |              |- SELECT user FOR UPDATE / none       |               |
```

The full diagram, with lifelines lined up, follows. Each line is one message.

```
Client          API               Postgres            Worker         Provider
   |              |                 |                   |               |
   |-- POST ----->|                 |                   |               |
   |              |                 |                   |               |
   |              |- SELECT user FOR UPDATE ->          |               |
   |              |                 |                   |               |
   |              |<---- user / none                    |               |
   |              |                 |                   |               |
   |              |- COUNT 60min -->|                   |               |
   |              |<-- count is N --|                   |               |
   |              |                 |                   |               |
   |              |- write token -->|                   |               |
   |              |                 |                   |               |
   |              |- COMMIT ------->|                   |               |
   |              |                 |                   |               |
   |<-- generic --|                 |                   |               |
   |              |                 |<-- claim job -----|               |
   |              |                 |----- job row ---->|               |
   |              |                 |                   |- send email ->|
   |              |                 |                   |<-- 250 OK ----|
   |              |                 |<-- delete job ----|               |
```

Note: the diagram above was drawn with the `FOR UPDATE` and the `COUNT` against the same user. The steps are:

1. `BEGIN`, then `SELECT` the user row by normalised email, `FOR UPDATE`. If there is no user, `COMMIT` and return the generic body. Nothing is inserted and no job is queued.
2. Count tokens for this user created in the last 60 minutes. If the count is 3 or more, `COMMIT` and return the generic body. No new link, no email.
3. Otherwise, in the same transaction, mark any live link for this user as `superseded_at = now()`, insert the new token row, and insert the reset email job.
4. `COMMIT`, then return the generic body. The worker claims the job, sends it and deletes it.

Notes:

- The user-row lock makes the rate-limit count exact under concurrent requests.
- The old link dies in the same commit that creates the new one. If the job insert fails, the whole transaction rolls back and the old link stays live.
- The raw token is generated as 32 bytes from a CSPRNG and base64url-encoded. It goes into the job payload and is never written to a table. Only its SHA-256 is stored.
- The email queue is assumed to be a Postgres table (`email_jobs`) that the worker claims with `FOR UPDATE SKIP LOCKED`. This is what allows the job insert to share the transaction. See open question 1 if the queue is external.
- Timing: the unknown-address path skips the insert and the job, so it is faster. Pad every response to a fixed minimum time that is above the slowest path, so that latency does not reveal whether an account exists.

## 2. Link-click and submit flow

```
Client          API               Postgres
   |              |                 |
   |- POST check->|                 |
   |              |- SELECT hash -->|
   |              |<---- row or none|
   |<-- status ---|                 |
   |   (form or expired page)       |
   |              |                 |
   |- POST reset->|                 |
   |              |  validate password locally (length, breached list); no write on failure
   |              |                 |
   |              |- burn token --->|   BEGIN; UPDATE ... WHERE live RETURNING user_id
   |              |<---- 1 or 0 rows|
   |              |- hash, kill --->|   set password_hash; DELETE sessions WHERE user_id;
   |              |                 |   insert "password changed" email job
   |              |- COMMIT ------->|
   |<-- 303 /login|                 |
```

Notes:

- The reset link is `https://<app>/reset#<token>`. The fragment is never sent to the server, so it stays out of access logs and referrers. The reset page sets `Referrer-Policy: no-referrer` and calls `history.replaceState` to clear the fragment once it has read the token into memory.
- The check call is a POST with the token in the body, so the token does not reach logs through a query string. The check is read-only and does not burn the link.
- On submit, the order is: check the token is live, validate the password server-side (12 characters or more, not on the breached list, a maximum length such as 128 to bound hashing cost), then burn. A rejected password returns before any write, so the link is still usable.
- The burn is a conditional `UPDATE` that also checks `used_at IS NULL`, `superseded_at IS NULL` and `expires_at > now()`. This is what makes the link single-use under concurrent submits. Zero rows means rollback and the expired page.
- The password update, the session deletion and the "changed" email job are one transaction. If any step fails, the token, the password and the sessions all stay as they were.
- Sessions are deleted by `user_id`, which covers the device that did the reset. No session is created, so the user is not logged in.
- The breached-password check runs against a local list. The password is never sent to a third party.

## 3. Token lifecycle

```
                    issue (under the 3-per-hour limit)
                                  |
                                  v
                  +------------------------------+
                  |  ISSUED                      |
                  |  used_at = null              |
                  |  superseded_at = null        |
                  +------------------------------+
                     |             |            |
     30 min pass     |             |            |   new link issued for same user
   (no write; time   |             |            |
    check only)      v             |            v
          +------------------+     |   +--------------------+
          |  EXPIRED         |     |   |  SUPERSEDED        |
          |  (dead by time)  |     |   |  superseded_at set |
          +------------------+     |   +--------------------+
                                   |
                  successful reset commits
                                   v
                  +------------------------------+
                  |  USED                        |
                  |  used_at = now()             |
                  +------------------------------+
```

Notes:

- Only `ISSUED` is live. `USED` and `SUPERSEDED` are terminal. `EXPIRED` is a time check and needs no write.
- The check, the submit and the worker all test the same live condition, so there is one rule to keep correct.

## 4. Failure paths

```
SUBMIT (POST /complete)
 |
 +-- token not live (missing, expired, used, superseded)?
 |       --> 410 "this link has expired, request a new one". Nothing written.
 |
 +-- password under 12 chars, or on breached list?
 |       --> 422 form error. Token untouched. The user may retry until expiry.
 |
 +-- BEGIN
 |     burn token (conditional UPDATE)
 |       |-- 0 rows  (a second submit won the race, or expiry passed)
 |       |       --> ROLLBACK, 410 expired page
 |       |-- 1 row
 |             set password_hash, DELETE sessions, insert "changed" job
 |             COMMIT --> 303 /login
 |                 |-- DB error before COMMIT --> ROLLBACK, 500. Link still live.


WORKER (reset email job)
 |
 +-- token superseded, or past expires_at, when the job runs?
 |       --> drop the job without sending. Log at info.
 |
 +-- send via mail provider
 |       |-- 2xx  --> delete job row (and the raw token inside it)
 |       |-- fail --> retry with backoff (existing policy, max 3)
 |                 |-- still failing --> log error, drop job. Nobody is notified.
```

Notes:

- Rate-limit overflow looks identical to a normal request. This is the required behaviour, and the user is not told why.
- A dropped reset email leaves the user with no usable link, while the screen said "sent". Their retry is the recovery. Retries also count against the hourly limit, as the brief defines it.
- The worker skips superseded and expired jobs. Without this check, a retry could deliver an old link after a newer one has been issued, or after 30 minutes have passed.
- A dropped "password changed" email is the case the brief's mail behaviour already accepts: nobody is notified. Log it with the user id and alert on the count.
- A DB failure before commit rolls back the burn. The user can retry with the same link while it is still within its 30 minutes.

## Data

- New table `password_reset_tokens`: `id`, `user_id` (fk, not null), `token_hash` (unique, not null, SHA-256 of the raw token), `created_at`, `expires_at` (created plus 30 minutes), `used_at` (nullable), `superseded_at` (nullable). Index on `(user_id, created_at)` for the rate-limit count.
- Rows are purged 24 hours after creation. The rate limit needs only the last hour, so nothing else is kept. No raw token, IP address or user agent is stored in this table.
- `email_jobs`: a reset job carries the raw token until it is sent or dropped, then the row is deleted. The queue is access-controlled like other job payloads.
- `users`: only `password_hash` changes. `sessions`: rows for that user are deleted.

## Open questions

1. Queue location. If the queue is Postgres, the job insert shares the transaction as drawn. If it is external, enqueue after `COMMIT`. A crash in between leaves a superseded or unused token that nobody holds, so the cost is a user who must request again. I recommend confirming the queue location before implementation.
2. Raw token at rest in the job row. It lives only until send or drop. If that is unacceptable, encrypt the payload with a key the worker holds. Decision needed.
3. Alerting. Dropped reset jobs and dropped changed-password jobs should both emit a metric. The brief does not require this, but without it these failures are invisible.
4. Password maximum length. The brief sets only a minimum. I suggest 128 to bound hash cost. Decision needed.
5. Response padding. The fixed minimum time needs a measured value. Choose it from the slowest real path, not from a guess.