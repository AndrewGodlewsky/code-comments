## Brief: password reset by emailed link

We're adding "Forgot password?" to the consumer app. A user who can't log in enters their email address and gets a one-time link for setting a new password. Write the design as an **ASCII diagram in a fenced code block, with short notes** underneath. Cover the request flow, the link-click flow and the failure paths.

**Existing system.** The web client talks to our API server. Postgres holds `users` (including the password hash) and `sessions` (one row per logged-in device; the API checks it on every request). Outgoing mail already goes through an email queue: the API adds a job and an email worker sends it through our third-party mail provider. When a send fails, the worker retries up to 3 times with backoff. After that it logs the failure and drops the job, and nobody is notified.

**Fixed requirements.**

- The forgot-password endpoint always returns the same message: "If an account exists for that address, we've sent a link." Unknown addresses get this message too, and nothing is sent to them.
- An account can be sent at most 3 reset emails in any rolling hour. Requests over that limit still get the generic message, but no new link is created and no email is sent.
- The token is 32 random bytes and appears only inside the link. We store only its SHA-256 hash, never the raw token.
- A link is valid for 30 minutes after it is issued, and it works once.
- Issuing a new link immediately kills any earlier unused link for that account.
- The link opens a "choose a new password" page. Check the token when the page loads. If it is invalid, expired or already used, show a "this link has expired, request a new one" page instead. Check the token again when the form is submitted.
- A new password must be at least 12 characters and must not be on the breached-password list. If the password is rejected, the link stays usable and the user can try again until it expires.
- When a reset succeeds, store the new password hash, burn the link, and log the account out on every device, including the one that did the reset. Then send a "your password was changed" email and redirect the user to the login page. Do not log them in automatically.

What data you store and how the pieces coordinate is up to you. Keep it to what's needed.
