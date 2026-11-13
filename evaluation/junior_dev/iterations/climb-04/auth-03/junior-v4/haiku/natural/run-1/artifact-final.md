# Password reset by emailed link: design

## Summary

Today the API checks the `sessions` table on every request. Outgoing mail goes through an email queue: the API adds a job, and an email worker sends it. A failed send is retried 3 times, then logged and dropped. Nobody is told.

The new flow has three parts. A user who cannot log in enters their email address, and the API stores a hash of a one-time token and queues an email that holds the raw token. The user clicks the link and sets a new password. A successful reset uses the link up, deletes every session for the account, and sends a "your password was changed" email.

## Terms

- **Token**: 32 random bytes. It appears only inside the link. The database stores only its SHA-256 hash.
- **Reset row**: one row in `password_reset_tokens` for each link issued. Rows stay after use, so the hourly count stays correct.
- **Live**: a reset row is live when it is not used, not invalidated and not expired.
- **Email job**: an entry in the existing email queue. The worker sends it.
- **App key**: a server secret that only the API and the worker hold. It encrypts the raw token inside a queued job.
- **Session**: one row in `sessions` for each logged-in device.

## Diagram

```
FLOW 1: REQUEST A LINK

 Browser                API server                          Postgres
   |                        |                                   |
   | POST /password-reset   |                                   |
   | { email }              |                                   |
   |----------------------->| 1. normalize email                |
   |                        | 2. BEGIN; find user by email      |
   |                        |    and lock its row ------------->|
   |                        |    no user: COMMIT, go to 6       |
   |                        | 3. count reset rows for the user  |
   |                        |    created in the last hour       |
   |                        |    (used and invalid rows too) -->|
   |                        |    3 or more: COMMIT, go to 6     |
   |                        | 4. raw = 32 random bytes          |
   |                        |    hash = SHA-256(raw)            |
   |                        |    invalidate older unused rows ->|
   |                        |    insert reset row (hash,        |
   |                        |      expires_at = now + 30 min) ->|
   |                        |    insert email job (user_id,     |
   |                        |      reset row id, raw token      |
   |                        |      encrypted) ----------------->|
   |                        | 5. COMMIT ----------------------->|
   |                        | 6. reply 200 with the same text   |
   |<-----------------------|                                   |


FLOW 2: DELIVER THE EMAIL (email worker)

 email queue --> worker takes job --> job type?
                                        |               |
                                  reset link      password changed
                                        |               |
                          read reset row by id          |
                          live?  no --> clear payload,  |
                                        drop job, log  |
                                        | yes           |
                          decrypt raw token             |
                                        |               |
                                        +------+--------+
                                               |
                                    send to the account's email
                                    (users row, by user_id)
                                    via the mail provider
                                       |                |
                                      ok              fail
                                       |                |
                              clear payload,    retry up to 3 times,
                              mark sent         with backoff
                                                        |
                                          still failing: clear payload,
                                          log, drop job
                                          (no notice to the user)


FLOW 3: CLICK THE LINK AND SET A PASSWORD

 Browser                 API server                        Postgres
   |                         |                                 |
   | GET /reset?token=RAW -->| hash = SHA-256(RAW)             |
   |                         | find reset row by hash -------->|
   |                         |<--------------------------------|
   |                         | read only, nothing is written   |
   |<-- not live: expired page                                 |
   |<-- live: form, RAW in a hidden field                      |
   |    (Referrer-Policy: no-referrer)                         |
   |                         |                                 |
   | POST /reset/confirm --->| hash RAW                        |
   | { token, new_password } | check live (no lock)            |
   |                         |   not live: expired page        |
   |                         | check password: at least 12     |
   |                         |   characters, not breached;     |
   |                         |   hash it (no transaction open) |
   |<-- rejected: form error, link stays usable                |
   |                         | BEGIN                           |
   |                         | lock reset row; check live      |
   |                         |   not live: ROLLBACK, expired   |
   |                         | UPDATE users SET password_hash  |
   |                         | DELETE sessions WHERE user_id   |
   |                         | mark reset row used             |
   |                         | insert "password changed" job   |
   |                         | COMMIT ------------------------->|
   |<-- 303 redirect to /login (no automatic login)            |
```

## Steps

Flow 1 (request a link). It starts when `POST /password-reset` arrives. The numbers match the diagram.

1. **Normalize the email.** Trims and lowercases it. Keeps nothing. Cannot fail.
2. **Find the user and lock its row.** Opens a transaction, finds the user by email and locks the row, so two requests for one account run one after the other. Keeps `users`. If there is no user, commit and go to step 6. An unknown address has no row to lock, so it only reads.
3. **Count recent links.** Counts the user's reset rows created in the last hour, including used and invalidated rows. Keeps `password_reset_tokens`. If the count is 3 or more, commit and go to step 6.
4. **Issue the link.** Makes 32 random bytes and stores their SHA-256 hash. Invalidates older unused rows. Inserts a reset row that expires 30 minutes from now. Inserts an email job with the reset row id and the raw token encrypted with the app key. If any write fails, the whole transaction rolls back.
5. **Commit.** Commits the reset row and the email job together. Nothing is kept unless the whole transaction commits.
6. **Reply.** Returns 200 with the generic text, which is the same for known and unknown addresses. The reply does not wait for the email.

Flow 2 (the email worker). It starts when the worker takes a job from the email queue.

1. **Read the job type.** It is either `reset_link` or `password_changed`. Keeps nothing.
2. **Check the link (reset link only).** Reads the reset row by its id. If the row is not live, clears the payload, drops the job and logs it. Keeps the reset row. Password-changed jobs skip this step.
3. **Decrypt the token (reset link only).** Uses the app key. Keeps nothing new.
4. **Send.** Reads the email address from the `users` row by `user_id`, then sends through the mail provider. The job holds no address. On success, clears the payload and marks the job sent. On failure, retries up to 3 times with backoff. If it still fails, clears the payload, logs it and drops the job. The user is not told.

Flow 3 (click the link and set a password). It starts when the browser sends `GET /reset?token=RAW`.

1. **Open the link.** Hashes RAW and finds the reset row by hash. This step only reads, so a mail scanner that opens the link does not use it up. If the link is not live, the browser gets the expired page. If it is live, the browser gets the form, with RAW in a hidden field and `Referrer-Policy: no-referrer`.
2. **Check the link again on submit.** `POST /reset/confirm` sends the token and the new password. Hashes RAW and checks that the link is live, without a lock. If it is not live, the browser gets the expired page.
3. **Check and hash the password.** It must be at least 12 characters and must not be on the breached-password list. The hash is made before the transaction opens, so no lock is held during the breach lookup. If the password is rejected, the browser gets a form error and the link stays usable.
4. **Use the link in one transaction.** Begins a transaction, locks the reset row and checks that it is still live. If it is not, rolls back and shows the expired page. Otherwise it updates `users.password_hash`, deletes every `sessions` row for the user, marks the reset row used, inserts a "password changed" email job, and commits. If any write fails, the whole transaction rolls back: the link is unused, the password is unchanged and the sessions are kept.
5. **Redirect.** Sends a 303 to `/login`. The user is not logged in automatically.

Change to the existing login. The login reads the user row, checks the password and inserts the session in one transaction. It locks the user row with `SELECT ... FOR SHARE` while it does this. The reset's `UPDATE users` waits for that lock. So either the login finishes first and the reset then deletes its session, or the login starts after the reset and sees the new hash. Sessions need no timestamp check.

## Data

- `password_reset_tokens` (new): `id`, `user_id` (foreign key to `users`), `token_hash` (32 bytes, unique), `created_at`, `expires_at`, `used_at` (nullable), `invalidated_at` (nullable). Index on `(user_id, created_at)`. Purge rows older than 24 hours.
- `users`: no schema change.
- `sessions`: no schema change. The reset deletes every row for the user.
- Email job: `type` (`reset_link` or `password_changed`) and `user_id`. A `reset_link` job also has the reset row `id` and the raw token, encrypted with the app key. The job holds no email address. The payload, including the encrypted token, is cleared when the job is sent or dropped.

## Failure paths

| Case | What happens |
|---|---|
| Unknown email | No row, no token, no email. Same generic reply. |
| 3 or more links in the last hour | Same generic reply. No reset row, no email job. |
| Database error while requesting a link | Full rollback. Nothing is queued. The user sees a server error. |
| Email send fails 3 times | The worker logs it and drops the job. The user still sees the generic reply. The link stays live but unseen, and expires after 30 minutes. |
| Newer link issued | Older unused links are invalidated at once. Their pages show the expired page. The worker's live check drops their queued emails. |
| Link not live when the page loads | Expired page. Nothing changes. |
| Link expires while the form is open | Submit re-checks the link and shows the expired page. |
| Weak or breached password | Form error. The link is not used up and stays usable until it expires. |
| Two submits at once | The second waits on the row lock, then sees the link used and gets the expired page. |
| Database error during the reset | Full rollback. Link unused, password unchanged, sessions kept. |
| "Password changed" email fails | The reset still stands. The worker retries, then logs and drops the job, as in Flow 2. |
| Login racing the reset | The login's row lock decides. Either the reset deletes the new session, or the login fails because the hash has changed. |

## Open questions

1. **Raw token in the queue.** Decided: encrypt it with the app key and clear the payload when the job is sent or dropped. Anyone with the app key and read access to the queue table could recover a live raw token. The brief says the raw token appears only in the link, so this needs sign-off.
2. **Quota counts links issued, not emails delivered.** A dropped email still uses one of the 3 slots. Confirm this is acceptable.
3. **Dropped emails are silent.** Ops needs an alert or metric for dropped reset and "password changed" jobs. This version has no "didn't get the email?" path.
4. **Token in the URL.** Query strings must stay out of access logs and error reports. The form page sends `Referrer-Policy: no-referrer`.
5. **No per-IP limit** on the request and confirm endpoints in this version. The 256-bit token makes guessing infeasible.
6. **Breached-password check.** Choose a k-anonymity range lookup or a local list. Either way it runs outside the transaction.
7. **Where the email queue lives.** The design assumes Postgres, so the email job is written in the same transaction as the reset row. If the queue is not in Postgres, a crash between commit and queueing leaves a live link with no email. The brief also does not say how the worker finds new jobs (polling, notification or an external queue). This is needed before implementation.
8. **Reply timing.** A known and an unknown address may differ in reply time by a few milliseconds. Replies are not padded. Decide whether this matters.