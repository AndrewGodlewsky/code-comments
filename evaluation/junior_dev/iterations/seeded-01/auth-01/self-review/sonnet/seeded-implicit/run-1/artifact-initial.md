## Auth plan

Server-side sessions in Postgres, cookie `sid`. Tables: users, sessions, login_failures, login_locks.

```mermaid
sequenceDiagram
    participant B as Browser
    participant A as App
    participant DB as Postgres
    B->>A: POST /login
    A->>DB: check login_locks
    A->>DB: look up user
    A->>A: check password
    A->>DB: create session
    A-->>B: set sid cookie, redirect
    B->>A: GET page
    A->>DB: validate session
    A-->>B: page or redirect to /login
    B->>A: POST /logout
    A->>DB: delete session
    A-->>B: redirect to /login
```

Notes:
- Lockout: 5 fails / 10 min, 15 min lock.
- Cookie flags: HttpOnly, Secure, SameSite=Lax.
- Timeouts: 30 min idle, 12 h max.
- Bad login goes back to the login page with an error.
- New session ID on each login.
- Cleanup job for expired rows.
- Handle DB errors.
