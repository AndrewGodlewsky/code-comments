# Password reset by emailed link

## What this is

Today the web client calls the API server, which reads and writes Postgres (`users`, `sessions`). Outgoing email goes through a queue. An email worker sends each job through the mail provider and retries a failed send 3 times, then drops the job and tells no one.

This adds a "Forgot password?" flow. A user who cannot log in asks for a reset link by email. The link opens a page where they set a new password once, within 30 minutes. Setting the password logs them out on every device.

## Terms

- **Reset token**: 32 random bytes. It appears only inside the link. The server stores only its SHA-256 hash.
- **reset_tokens**: a new table with one row per issued link: account, token hash, created time, expiry time, and a used flag.
- **Session**: one row in `sessions` per logged-in device. The API checks it on every request.
- **Generic message**: "If an account exists for that address, we've sent a link."

## Diagram

```
 Browser ---> API server ---> Postgres
                  |           (users, sessions, reset_tokens)
                  |
                  +---> Email queue ---> Email worker ---> Mail provider

 Forgot password:  submit email -> look up user -> rate limit
                   -> create token -> email link -> respond

 Open link:        validate token -> show new-password form

 Set password:     validate token -> check password -> save password
                   -> revoke sessions -> confirmation email -> login page
```

## Steps

### 1. Request a link

- **Starts:** the user submits their email on the "Forgot password?" form.
- **Does:**
  1. Look up the account for the address. If there is none, return the generic message and stop. Send nothing.
  2. Count this account's `reset_tokens` rows created in the last hour. If there are 3 or more, return the generic message and stop. Create no link and send no email. Any earlier link stays valid.
  3. In one database transaction, mark every unused link for this account as used, then insert a new row with the token's hash and an expiry 30 minutes away.
  4. Queue the reset email. The raw token goes only inside the link.
  5. Return the generic message.
- **Data kept:** `users` (read), `reset_tokens` (new row). Old rows stay, marked used, so step 2 can count them.
- **If it goes wrong:** a database error in step 1 or 3 returns a server error. Nothing is saved or sent.

### 2. Open the link

- **Starts:** the user clicks the link.
- **Does:** hash the token, find its row, and check that the link is unused and not past its expiry. If it passes, show the "choose a new password" form. If not, show the expired page: "This link has expired, request a new one."
- **Data kept:** reads `reset_tokens`. Changes nothing.
- **If it goes wrong:** a database error shows a server error.

### 3. Set the new password

- **Starts:** the user submits the form with the token and a new password.
- **Does:**
  1. Check the token again, as in step 2. If it fails, show the expired page.
  2. Check the password: at least 12 characters, and not on the breached-password list. If it fails, show the reason on the form. The link stays usable until it expires.
  3. In one database transaction, store the new password hash in `users`, mark the link used, and delete the account's rows in `sessions`. This logs out every device, including this one.
  4. Queue the "your password was changed" email.
  5. Redirect to the login page. Do not log the user in.
- **Data kept:** `users` (password hash), `reset_tokens` (used flag), `sessions` (rows deleted), the email queue.
- **If it goes wrong:** a database error in step 3 rolls back. Nothing changes, the link stays usable, and the user sees an error.

## What fails

| Where | What goes wrong | What happens |
|---|---|---|
| Request | Unknown address | Generic message. Nothing sent. |
| Request | 3 or more links in the last hour | Generic message. No link, no email. Earlier link stays valid. |
| Request | Database error | Server error. Nothing saved or sent. |
| Request or confirmation | Mail provider keeps failing | Worker retries 3 times, then drops the job. Nobody is told. |
| Open or submit | Token invalid, expired or used | Expired page. |
| Submit | Password under 12 characters, or breached | Form shows the reason. Link stays usable until it expires. |
| Submit | Database error on save | Nothing changes. Error shown. Link stays usable. |

## Open questions

- If the reset email is dropped after the link is saved, the user has a link they never received and nobody is told. The brief does not say what to do. Not decided.
- Where does the breached-password list come from, and how is it kept current? Not decided.