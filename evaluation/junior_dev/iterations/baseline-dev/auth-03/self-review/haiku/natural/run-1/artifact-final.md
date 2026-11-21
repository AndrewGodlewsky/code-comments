# Password reset by emailed link: design

## What this does

A user who cannot log in enters their email address. If an account exists for that address, they get a one-time link to choose a new password. The link is valid for 30 minutes. The reply is the same whether or not the account exists, so the page never reveals which addresses have accounts.

## The parts

- **Web client**: the browser page the user sees.
- **API server**: handles every request.
- **Postgres**: our database. It holds `users` (including each user's password hash) and `sessions` (one row per logged-in device; the API checks it on every request).
- **Queue and email worker**: the API puts an email job on a queue. A separate worker process takes jobs off the queue and sends them through a third-party mail provider. If a send fails, the worker retries up to 3 times, waiting a little longer each time. After that it logs the failure and drops the job. Nobody is notified.
- **New table**: `password_reset_tokens`, described in section 3.

## Terms

- **Token**: a random secret that proves the person controls the email address. It appears only inside the reset link.
- **SHA-256 hash**: a one-way fingerprint of a value. We store the fingerprint of the token, not the token itself, so a database leak does not expose usable links.
- **Usable link**: a link that is not used, not invalidated, and not expired. Any other link is dead and shows the expired page.
- **Invalidated**: switched off on purpose. This happens when a newer link is issued, or when the email for the link cannot be queued or sent.
- **Used**: a link that a successful reset has consumed (`used_at` is set).
- **Transaction**: a group of database writes that all succeed or all roll back together.
- **Row lock (`SELECT ... FOR UPDATE`)**: other requests that need the same row wait until the transaction holding the lock finishes.
- **Password hash (argon2 or bcrypt)**: a slow, salted, one-way scramble of the password. The password itself is never stored.
- **Breached-password list**: a local list of passwords that appeared in past data leaks. We reject any password on it.
- **Rolling hour**: the 60 minutes before the request, not a fixed clock hour.

## 1. Request flow: `POST /password-reset { email }`

```
  Browser        API server         Postgres       Queue + worker     Mail provider
     |                |                 |                 |                 |
     |-- email ------>|                 |                 |                 |
     |                |-- find user --->|                 |                 |
     |                |<-- user found --|                 |                 |
     |                |-- 2 to 7: tx -->|                 |                 |
     |                |-- 8. add email job --------------->|                 |
     |                |                 |                 |-- 9. send ----->|
     |<-- generic ----|                 |                 |                 |
```

Inside the transaction (steps 2 to 7):

1. Find the user by email. If there is no such user, stop. Reply with the generic message. Nothing is written and no email is sent.
2. BEGIN.
3. Lock the user row. Other requests for this account now wait.
4. Count the links issued for this account in the last hour. If the count is 3 or more, COMMIT with no changes and stop. Reply with the generic message. No new link and no email. The old link stays usable.
5. Invalidate the account's older usable links.
6. Insert the new link: store its hash and set it to expire in 30 minutes.
7. COMMIT.
8. Add the email job to the queue.
9. The worker sends the email, retrying up to 3 times. The email contains `/reset?token=T`.

Notes:

1. Every outcome returns the same text and status code. Every reply is padded to a fixed minimum time, so response timing does not reveal whether the account exists.
2. Step 3 locks the user row, so requests for the same account run one at a time. That keeps the count in step 4 exact. The count includes every link issued in the last hour, even links that were later invalidated or whose email later failed.
3. Step 5 runs only after the limit check passes. A rate-limited request never invalidates the earlier link.
4. Step 8 runs after the commit, so the email job is added only after the link is saved. If adding the job fails, mark the new link invalidated, log it, and still return the generic message. Writing the job inside the step 7 transaction is an open decision (section 5).

## 2. Link-click flow: `GET /reset?token=T`, then `POST /reset`

```
  Browser                  API server                       Postgres
     |                         |                                |
     |-- 1. GET reset -------->|  h = SHA-256(T)                |
     |                         |-- 2. find link ------------->  |
     |                         |<-- usable or nothing ------    |
     |<-- form page -----------|  (GET writes nothing)          |
     |<-- expired page --------|  if nothing usable             |
     |                         |                                |
     |-- POST form ----------->|  reset steps (below)           |
     |                         |-- 4 to 9: one transaction -->  |
     |                         |<-- committed -------------     |
     |<-- 303 to /login -------|                                |
```

Notes on the GET:

- The GET only reads. Email security scanners often open links automatically to check them. Because the GET changes nothing, a scanner cannot use up the link.
- The first check (the GET) shows the form only if the link is usable. Otherwise it shows the expired page.

The POST `/reset` steps, with `T` (the token) and the new password from the form:

1. Check the token again with the same usable test. If the link is not usable, show the expired page and stop.
2. Check the password: at least 12 characters, and not on the breached-password list. This check is local and needs no database. If it fails, show a form error and stop. The link is not touched and stays usable.
3. Hash the password.
4. BEGIN a transaction.
5. Lock the link row (`FOR UPDATE`) and check it again. If it is not usable, ROLLBACK and show the expired page.
6. Set `users.password_hash` to the new hash.
7. Set `used_at = now()` on the link.
8. Delete all `sessions` rows for the user, which logs them out on every device, including this one.
9. COMMIT.
10. Add a "your password was changed" email job. Redirect with 303 to the login page. Do not create a session.

Notes on the POST:

1. The token is checked twice. The first check is cheap and runs before the slow password hash. The second check runs under a row lock inside the transaction. If two submits of the same link race, one succeeds. The other waits for the lock, sees the link already used, and gets the expired page.
2. Steps 6 to 8 are one transaction. The new password, the used link and the logout either all happen or none of them do.
3. Step 10 runs after the commit. If it fails, the reset still stands. The queue retries the email, and the failure is logged.
4. The raw token appears in the URL only on the GET. The reset page sends `Referrer-Policy: no-referrer`, so the URL is not passed to other sites. Keep the raw token out of access logs where the server stack allows it. The form sends the token in the POST body, not in the URL.

## 3. Data

There is one new table. The rate limit uses it too. No other table stores tokens.

```
password_reset_tokens
  id              bigserial     primary key
  user_id         bigint        not null, references users(id) on delete cascade
  token_hash      bytea         not null, unique      -- SHA-256 of the 32-byte raw token
  created_at      timestamptz   not null default now()
  expires_at      timestamptz   not null              -- created_at + 30 minutes
  used_at         timestamptz                         -- set when a reset succeeds
  invalidated_at  timestamptz                         -- set when a newer link replaces it,
                                                      --   or when queuing or sending fails
  index (user_id, created_at)

users:     password_hash is replaced on success. Nothing else changes.
sessions:  all rows for the account are deleted on success. Nothing else changes.
```

Notes:

- **Retention**: delete rows whose `created_at` is more than 1 hour old. The rate limit never looks further back than that.
- **Raw token**: 32 random bytes from a cryptographically secure random source, sent as 43 URL-safe characters in the link. It is never stored in Postgres and never written to logs.
- **Queue exposure**: the email job contains the link, so the raw token sits in the queue until the send succeeds or the job is dropped. Keep jobs short-lived and limit who can read the queue.
- **Config values**: link lifetime 30 minutes, cap of 3 links per rolling hour, minimum password length 12 characters.

## 4. Failure paths

1. **Unknown email**: generic message. No writes, no email.
2. **Over the hourly cap (3 links in the last hour)**: generic message. No new link and no email. The earlier link stays usable.
3. **Adding the email job fails**: mark the new link invalidated, log it, and still return the generic message.
4. **Mail send fails 3 times**: the worker logs the failure, marks the link invalidated, raises an alert, and drops the job. The user sees nothing, because they were already told a link was sent. Failed sends still count toward the hourly cap, so a user can be blocked for up to an hour after three failures. This is the conservative default and an open decision (section 5).
5. **Link expired, used or invalidated when the page loads**: expired page. No writes.
6. **Link submitted after it expired or was used**: expired page. The transaction rolls back, so nothing changes.
7. **Password too short or on the breached list**: form error. No writes. The link stays usable until it expires.
8. **Breached-password list unavailable**: reply "try again later." This fails closed: a password that was not checked is never accepted.
9. **Database error during the reset transaction**: roll back. The link stays usable.
10. **Password-changed email fails**: the reset stands. The queue retries the email, and the failure is logged.
11. **Two submits of one link**: the first succeeds. The second waits on the row lock, then sees the link used and gets the expired page.
12. **Two requests for one account at the same time**: the row lock makes them run one after the other, so the hourly cap holds.

## 5. Open decisions

- **Should failed sends count toward the cap?** (See path 4.) The current default counts every issued link.
- **Should the email job be written in the same transaction as the link insert (the outbox pattern)?** That means saving the link and its email job in one transaction, so a link is never saved without its job. The answer depends on whether the queue lives in Postgres. Today it does not.
- **The generic message says "we've sent a link" even if the send later fails.** The brief fixes this wording, so monitor drop rates and alert on them.
- **Logs record only `user_id` and `token_id`.** They never contain the raw token, the link or the password.