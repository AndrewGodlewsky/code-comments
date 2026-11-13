# Password reset by emailed link

## Summary

A user who cannot log in enters their email address and receives a one-time link to set a new password. The request step always gives the same reply, so it never reveals whether an account exists. Today the API checks a `sessions` row on every request, and outgoing mail goes through an email queue that a worker drains. This feature adds a `reset_tokens` table, three API calls (request the link, open the link, submit a new password) and reuses the existing email queue.

## Terms

- **Token**: a random secret of 32 bytes. It appears only inside the emailed link.
- **Hash (SHA-256)**: a one-way fingerprint of the token. The server stores only the hash, so a leaked database does not reveal a usable link.
- **Session**: one row in `sessions` per logged-in device. Logging out means deleting these rows.
- **Email queue**: a list of email jobs. The API adds a job, and the email worker sends it through the mail provider.
- **Burn**: mark a link as used so that it can never work again.

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

1. **Request a link.** The user submits an email address. If no account has that address, the API returns the generic reply and stops. If the account already has 3 links created in the last hour, the API returns the generic reply and stops; no link is made and no email is sent. Otherwise the API marks any earlier unused link for that account as used, creates a new token, stores its hash with an expiry 30 minutes later, adds an email job containing the link to the queue, and returns the generic reply. The generic reply is exactly: "If an account exists for that address, we've sent a link."
2. **Open the link.** The page takes the token from the link, hashes it, and looks for a row with that hash that is unused and not expired. If it finds one, it shows the "choose a new password" form. If not, it shows "this link has expired, request a new one." Nothing changes in the database.
3. **Submit a new password.** The API repeats the check from step 2. It then checks the password: at least 12 characters, and not on the breached-password list. If the password fails, the form shows the reason again, and the link stays unused until it expires. If the password passes, one database transaction does three things. It marks the link as used, but only if it is still unused, so two submits with the same link cannot both succeed. It saves the new password hash in `users`. It deletes every `sessions` row for that user, including the device that made the reset. After the transaction, the API adds a "your password was changed" email to the queue and redirects to the login page. It does not log the user in.
4. **Send the email.** The email worker sends each queued job. If a send fails, it retries up to 3 times with backoff. After that it logs the failure and drops the job. Nobody is told.

Rules that apply to all steps:
- A token is valid for 30 minutes after it is issued, and it works once.
- Issuing a new link immediately ends any earlier unused link for that account.
- Each link created counts as one reset email toward the limit of 3 per account in any rolling hour.

## What goes wrong

| Failure | What happens |
|---|---|
| Unknown email address | Generic reply. Nothing is stored or sent. |
| Over 3 links in the last hour | Generic reply. No link, no email. |
| Link expired or used, on page load or on submit | "This link has expired, request a new one." |
| Password too short or on the breached list | Form shows the reason. Link still works until it expires. |
| Two submits with the same link | One succeeds. The other gets the expired page. |
| Database error during submit | Transaction rolls back. Password is unchanged and the link still works until it expires. |
| Reset email fails 3 times | Worker logs it and drops it. The user gets no email and nobody is notified. The user can request again if under the limit. |
| Confirmation email fails 3 times | Password change still stands. The worker drops the email as above. |

## Open questions

- A user whose link email is dropped is never told. The brief does not say whether that should change.
- Until it is sent, the queue job holds the email text, which includes the raw token. The brief says the token appears only inside the link. Whether queue storage is acceptable is not decided.
- Used and expired rows in `reset_tokens` are not deleted in this design. The cleanup schedule is not set.
- The source and update schedule of the breached-password list are not set.