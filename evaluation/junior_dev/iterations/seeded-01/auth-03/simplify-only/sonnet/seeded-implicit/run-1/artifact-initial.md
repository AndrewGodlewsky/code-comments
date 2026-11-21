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

Notes
- Tokens are random and stored hashed (SHA-256).
- Links last 30 minutes and work once.
- The forgot-password response is generic.
- Rate limit: 3 per hour.
- Password policy: 12+ characters, breached-list check.
- The email worker has the usual retries.
