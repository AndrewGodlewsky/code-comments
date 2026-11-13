## Password reset by emailed link

A user who cannot log in enters their email address on "Forgot password?" and receives a one-time link. The link opens a page where they choose a new password. When that succeeds, every device is logged out and the user goes to the login page.

Today the web client talks to the API server. Postgres holds `users` (with the password hash) and `sessions` (one row per logged-in device, checked on every request). The API sends mail by adding a job to the email queue. An email worker sends it through the mail provider. If a send fails, the worker retries 3 times with backoff, then logs the failure and drops the job. Nobody is told.

Terms
- Token: 32 random bytes. It appears only inside the emailed link.
- Token hash: the SHA-256 of the token. This is all we store.
- `reset_tokens`: the one new Postgres table. Each row holds the account, the token hash, when it was issued, and whether it is used or replaced.
- Live link: a link that is under 30 minutes old, unused, and not replaced by a newer link.

```
 Browser ---> API server ---> Postgres
                  |           (users, sessions, reset_tokens)
                  |
                  +---> Email queue ---> Email worker ---> Mail provider

 1. Forgot password
    submit email -> look up user -> rate limit
    -> kill earlier live links -> create token -> queue email -> generic reply

 2. Open link
    check token -> valid:   show new-password form
                -> invalid: show "link expired, request a new one" page

 3. Set password
    check token again -> check password -> save password hash
    -> burn link -> delete all sessions -> queue "password changed" email
    -> redirect to login page (no automatic login)
```

Steps

1. Forgot password
   - Starts when: the user submits an email address.
   - Does: the API looks up the user. If there is none, it does nothing more. If the account already has 3 links issued in the last rolling hour, it does nothing more. Otherwise it marks any earlier live link dead, stores a new `reset_tokens` row (hash only), and queues the email with the raw token in the link.
   - Data kept in: `reset_tokens`. The hourly count is the number of rows issued for that account in the last hour.
   - Always replies: "If an account exists for that address, we've sent a link." This is the same for unknown addresses and over-limit requests.

2. Open link
   - Starts when: the user clicks the link.
   - Does: the API hashes the token and looks for a live row. If found, it shows the new-password form. If not (invalid, expired or used), it shows the "this link has expired, request a new one" page.
   - Data kept in: `reset_tokens`. Nothing is changed.

3. Set password
   - Starts when: the user submits the form.
   - Does: the API checks the token again. Then it checks the password: at least 12 characters and not on the breached-password list. If both pass, it saves the new password hash in `users`, burns the link, deletes all of the account's rows in `sessions` (including the device that did the reset), queues a "your password was changed" email, and redirects to the login page.
   - Data kept in: `users`, `reset_tokens`, `sessions`.

Notes
- Each step behaves the same whether the account exists or not, as far as the user can see. Only the forgot-password reply is generic; the other pages are reached only with a token.
- A link is live for 30 minutes and works once. A newer link kills older ones.
- The email worker keeps its existing retry rules. Both the reset email and the "password changed" email use them.

What happens when things fail

| Where | What goes wrong | What happens |
|---|---|---|
| Forgot password | Unknown address | Generic reply. No link, no email. |
| Forgot password | Over 3 links in the hour | Generic reply. No link, no email. |
| Open link | Token invalid, expired or used | "Link expired" page. |
| Set password | Token no longer live at submit | "Link expired" page. Password not changed. |
| Set password | Password too short or breached | Form shows an error. The link stays live until it expires, so the user can try again. |
| Email worker | Send fails | Existing behaviour: 3 retries, then logged and dropped. Nobody is notified. |

Open questions
- If a reset email is dropped after its retries, the user gets no link and no message. They can only request again. The brief does not say whether this is acceptable.
- The "password changed" email can also be dropped silently. Nothing else depends on it.