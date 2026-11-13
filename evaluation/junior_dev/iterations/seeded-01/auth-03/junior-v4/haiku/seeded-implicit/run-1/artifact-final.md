# Password reset by emailed link

## What this is

Today the API adds an email job to a queue. An email worker sends it through the mail provider. If sending fails, the worker retries 3 times, then drops the job and tells nobody. This design adds a `reset_tokens` table and a reset flow. A user who cannot log in asks for a reset email. The link in that email opens a "choose a new password" form. A valid submit saves the new password, uses up the link, logs the user out of every device and sends a confirmation email.

## Terms

- **Token**: 32 random bytes. It goes only inside the link. We store only its SHA-256 hash.
- **reset_tokens**: one row per link issued. It holds the hash, the user, the expiry, and when the link was used or revoked.
- **Revoked**: an unused link that a newer link replaced. It can never work again.
- **Revoke sessions**: delete every `sessions` row for the user. This logs them out on every device.
- **Generic message**: "If an account exists for that address, we've sent a link." The page shows it whenever no link is sent.

## Diagram

```
 Browser ---> API server ---> Postgres (users, sessions, reset_tokens)
                  |
                  +---> Email queue ---> Email worker ---> Mail provider

 1 REQUEST LINK   email -> user found? -> fewer than 3 rows in last hour?
                    no to either: generic message, stop
                  yes: in one transaction, revoke older unused rows and
                       insert the new row (hash, expires in 30 min)
                  enqueue reset email with the token, then generic message

 2 OPEN LINK      token -> hash -> row valid? (not expired, used or revoked)
                    yes: show "choose a new password" form
                    no:  show "this link has expired, request a new one"
                  Nothing is changed.

 3 SET PASSWORD   token -> hash -> row valid?  (no: expired page)
                  password 12+ characters and not breached?
                    no: show form again, link stays usable
                  yes: in one transaction, store new hash, mark row used,
                       delete the user's sessions
                  enqueue "password changed" email, redirect to login
```

## Notes

- Steps 2 and 3 find the row, and so the user, from the token's hash. The token holds no user id.
- The form posts back to the same link address, so the token stays in the URL.

## Steps

### 1. Request link

- **Starts when**: the user submits an email on the "Forgot password" page.
- **What it does**:
  1. Find the user by email. If there is none, show the generic message and stop.
  2. Count the user's `reset_tokens` rows created in the last hour. This includes revoked and used rows. If there are 3 or more, show the generic message and stop.
  3. Make 32 random bytes and encode them for the URL. Compute the SHA-256 hash of the raw bytes.
  4. In one transaction, revoke the user's older unused rows and insert the new row: hash, created_at, expires_at = created_at + 30 minutes, and empty used_at and revoked_at.
  5. Queue the reset email, which holds the link with the raw token. Show the generic message.
- **Data**: `users`, `reset_tokens`, email queue.
- **If it goes wrong**: if the queue is down, the API still shows the generic message and logs the error. The new row expires unused, and the user must ask again.

### 2. Open link

- **Starts when**: the user clicks the link.
- **What it does**: hash the token from the link and find the matching row. If the row exists, is not expired, not used and not revoked, show the "choose a new password" form. Otherwise show the expired page. Nothing is changed.
- **Data**: `reset_tokens`, read only.
- **If it goes wrong**: an invalid, expired, used or revoked link shows the expired page: "this link has expired, request a new one." The page does not say which reason applies.

### 3. Set password

- **Starts when**: the user submits the form. The form posts back to the same link address.
- **What it does**:
  1. Check the token again, as in step 2. If it fails, show the expired page.
  2. Check the new password: at least 12 characters and not on the breached-password list. If it fails, show the form again. The link stays usable.
  3. In one transaction, store the new password hash, mark the row used and delete every `sessions` row for the user.
  4. Queue the "password changed" email. Redirect to the login page. Do not log the user in.
- **Data**: `users`, `reset_tokens`, `sessions`.
- **If it goes wrong**:
  - The transaction in step 3 fails: nothing changes and the link stays usable.
  - The email cannot be queued in step 4: the reset still stands, because step 3 has already committed. The user is still redirected to login. The error is logged. No confirmation is sent.

### 4. Send email (existing email worker)

- **Starts when**: a job is in the email queue.
- **What it does**: send the job through the mail provider. A sent job is removed from the queue. The job holds the raw token until it is sent or dropped.
- **Data**: email queue.
- **If it goes wrong**: the worker retries up to 3 times with backoff, then logs the failure and drops the job. Nobody is told, so the user gets no email and must ask again.

## Open questions

- Where does the breached-password list come from, and how often is it refreshed?
- What are the worker's backoff delays?
- The queue job holds the raw token until it is sent or dropped. Do the queue or the worker logs keep a copy of the job? Should the link be kept out of logs?
- Two requests at the same moment could both pass the 3-per-hour count. Accept this, or lock the user row?
- After 3 failed sends, the user gets no email and no notice. Accept this?